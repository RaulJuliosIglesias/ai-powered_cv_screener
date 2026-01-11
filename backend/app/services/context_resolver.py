"""
CONTEXT RESOLVER

Resolves pronoun-like references from conversation history.
Handles cases like "top candidate", "el mejor", "this person", etc.

Used by:
- RAG Service (before template selection)
- Query Understanding Service
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ResolvedReference:
    """Result of context resolution."""
    resolved: bool
    candidate_name: Optional[str] = None
    cv_id: Optional[str] = None
    reference_type: str = "none"  # "top_candidate", "pronoun", "this_candidate", etc.
    confidence: float = 0.0


# Patterns that indicate a reference to a previously mentioned candidate
REFERENCE_PATTERNS = [
    # Top/Best candidate references
    (r'\b(the\s+)?top\s+candidate\b', "top_candidate"),
    (r'\b(el\s+)?top\s+candidate\b', "top_candidate"),
    (r'\b(el\s+)?(mejor|best)\s+(candidato|candidate)\b', "top_candidate"),
    (r'\b(the\s+)?best\s+one\b', "top_candidate"),
    (r'\b(el\s+)?número\s+uno\b', "top_candidate"),
    (r'\b(the\s+)?#1\b', "top_candidate"),
    (r'\b#1\s*candidate\b', "top_candidate"),
    (r'\b(the\s+)?first\s+one\b', "top_candidate"),
    (r'\b(the\s+)?first\s+candidate\b', "top_candidate"),
    (r'\bfull\s+profile\s+of\s+(the\s+)?#\d+\b', "top_candidate"),
    (r'\bprofile\s+of\s+(the\s+)?#\d+\b', "top_candidate"),
    (r'\b(compare|comparar|compare\s+the\s+two\s+best)\b.*?(?:top\s+candidate|candidato|candidate)', "top_candidates"),
    (r'\b(compare|comparar)\s+(?:the\s+)?two\s+(?:best|top)\s+(?:candidates|candidatos)\b', "top_candidates"),
    
    # This/That candidate references
    (r'\b(this|that|ese|este|esta)\s+(candidato|candidate|person|persona)\b', "this_candidate"),
    (r'\babout\s+(him|her|them)\b', "pronoun"),
    (r'\b(sobre\s+)?(él|ella|ellos)\b', "pronoun"),
    
    # Generic references
    (r'\b(the\s+)?same\s+(candidate|person|candidato)\b', "same_candidate"),
    
    # PHASE 5.4: Follow-up question patterns (references to previous results)
    (r'\b(those|these|the)\s+(candidates|results|people)\b', "previous_results"),
    (r'\b(esos|estos|las?)\s+(candidatos?|resultados|personas)\b', "previous_results"),
    (r'\bmore\s+(info|information|details)\s+(about|on)\s+(them|those)\b', "previous_results"),
    (r'\b(the\s+)?senior\s+(developer|engineer|candidate)\b', "senior_candidate"),
    (r'\b(the\s+)?warning\s+signs\b', "risk_context"),
]


def has_reference_pattern(query: str) -> tuple[bool, str]:
    """
    Check if query contains a reference pattern that needs resolution.
    
    Args:
        query: User's query
        
    Returns:
        Tuple of (has_reference, reference_type)
    """
    q_lower = query.lower()
    
    for pattern, ref_type in REFERENCE_PATTERNS:
        if re.search(pattern, q_lower):
            return True, ref_type
    
    return False, "none"


def extract_candidate_from_history(
    conversation_history: List[Dict[str, str]],
    reference_type: str = "top_candidate"
) -> Optional[Dict[str, str] | List[Dict[str, str]]]:
    """
    Extract candidate information from conversation history.
    
    Looks for:
    - Ranking responses (to find #1 candidate)
    - Single candidate responses (last mentioned candidate)
    - Comparison responses (winner)
    - Multiple top candidates (for "compare the two best" queries)
    
    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": "..."}
        reference_type: Type of reference to resolve
        
    Returns:
        Dict with "name" and "cv_id" if found, None otherwise
        For "top_candidates": returns List[Dict] with top 2 candidates
    """
    if not conversation_history:
        logger.warning("[CONTEXT_RESOLVER] extract_candidate_from_history: No history provided")
        return None
    
    logger.info(f"[CONTEXT_RESOLVER] Searching {len(conversation_history)} messages for {reference_type}")
    
    # Special handling for "top_candidates" - return top 2 from ranking
    if reference_type == "top_candidates":
        return _extract_top_candidates_from_history(conversation_history)
    
    # PHASE 5.4: Handle previous_results - return all candidates from last response
    if reference_type == "previous_results":
        return _extract_previous_results(conversation_history)
    
    # PHASE 5.4: Handle senior_candidate - find senior level candidate
    if reference_type == "senior_candidate":
        return _extract_senior_candidate(conversation_history)
    
    # Look through history from most recent to oldest
    for idx, msg in enumerate(reversed(conversation_history)):
        if msg.get("role") != "assistant":
            continue
        
        content = msg.get("content", "")
        logger.info(f"[CONTEXT_RESOLVER] Checking assistant message {idx}, length={len(content)}")
        
        # PHASE 7.4 FIX: Pattern 0 - Look for "Top Recommendation:" with CV link first (most reliable)
        # Format: "Top Recommendation: [📄](cv:cv_xxx) **Name** (95%)"
        top_rec_cv_match = re.search(
            r'Top\s+Recommendation:?\s*\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*',
            content,
            re.IGNORECASE
        )
        if top_rec_cv_match:
            cv_id = top_rec_cv_match.group(1).strip()
            name = top_rec_cv_match.group(2).strip()
            logger.info(f"[CONTEXT_RESOLVER] PHASE 7.4: Found top recommendation with CV link: {name} ({cv_id})")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 1: Top Recommendation section (from ranking/job_match responses)
        # "Top Recommendation\n\nCarmen Rodriguez 3D\n96%"
        top_rec_match = re.search(
            r'Top\s+Recommendation[^\n]*\n+\**\[?([A-Z][a-záéíóúñ\s]+[A-Z]?[a-záéíóúñ\s]*)\]?\**',
            content, 
            re.IGNORECASE
        )
        if top_rec_match:
            name = top_rec_match.group(1).strip()
            cv_id = _extract_cv_id_for_name(content, name)
            logger.info(f"[CONTEXT_RESOLVER] Found top recommendation: {name}")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 2: #1 Top Pick (from ranking table)
        # "#1 Top Pick\n\nCarmen Rodriguez 3D"
        top_pick_match = re.search(
            r'#1\s+(?:Top\s+)?Pick[^\n]*\n+\**\[?([A-Z][a-záéíóúñ\s]+)\]?\**',
            content,
            re.IGNORECASE
        )
        if top_pick_match:
            name = top_pick_match.group(1).strip()
            cv_id = _extract_cv_id_for_name(content, name)
            logger.info(f"[CONTEXT_RESOLVER] Found #1 pick: {name}")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 3: CV link format **[Name](cv:cv_xxx)**
        cv_link_match = re.search(
            r'\*\*\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*',
            content
        )
        if cv_link_match:
            name = cv_link_match.group(1).strip()
            cv_id = cv_link_match.group(2).strip()
            logger.info(f"[CONTEXT_RESOLVER] Found CV link: {name} ({cv_id})")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 4: "Based on the analysis, Isabel Mendoza has the most experience"
        analysis_match = re.search(
            r'(?:based on|según|the analysis)[^,]*,?\s*\**\[?([A-Z][a-záéíóúñ\s]+)\]?\**\s+(?:is|has|tiene|es)',
            content,
            re.IGNORECASE
        )
        if analysis_match:
            name = analysis_match.group(1).strip()
            cv_id = _extract_cv_id_for_name(content, name)
            logger.info(f"[CONTEXT_RESOLVER] Found in analysis: {name}")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 5: Conclusion mentions first candidate
        conclusion_match = re.search(
            r':::conclusion[\s\S]*?\*\*\[?([A-Z][a-záéíóúñ\s]+)\]?\*\*',
            content,
            re.IGNORECASE
        )
        if conclusion_match:
            name = conclusion_match.group(1).strip()
            cv_id = _extract_cv_id_for_name(content, name)
            logger.info(f"[CONTEXT_RESOLVER] Found in conclusion: {name}")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 6: "emerges as the top choice" or "is the recommended candidate"
        top_choice_match = re.search(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*[^.]*(?:emerges as the top|is the recommended|top choice|overall score of 100)',
            content,
            re.IGNORECASE
        )
        if top_choice_match:
            cv_id = top_choice_match.group(1).strip()
            name = top_choice_match.group(2).strip()
            logger.info(f"[CONTEXT_RESOLVER] Found top choice: {name} ({cv_id})")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 7: Look for actual ranking with scores to find the real #1 candidate
        # Pattern: [📄](cv:cv_xxx) **Name** Score% - find the one with highest score
        ranking_matches = re.findall(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*[^0-9]*([0-9]+)%',
            content
        )
        if ranking_matches:
            # Find the candidate with the highest score
            best_match = max(ranking_matches, key=lambda x: int(x[2]))
            cv_id = best_match[0].strip()
            name = best_match[1].strip()
            score = best_match[2]
            logger.info(f"[CONTEXT_RESOLVER] Found #1 candidate by score: {name} ({cv_id}) with {score}%")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 7.5: Look for "Top Recommendation:" format with scores
        top_rec_matches = re.findall(
            r'Top\s+Recommendation:\s*\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*[^0-9]*([0-9]+)%',
            content,
            re.IGNORECASE
        )
        if top_rec_matches:
            cv_id = top_rec_matches[0][0].strip()
            name = top_rec_matches[0][1].strip()
            score = top_rec_matches[0][2]
            logger.info(f"[CONTEXT_RESOLVER] Found #1 via Top Recommendation: {name} ({cv_id}) with {score}%")
            return {"name": name, "cv_id": cv_id}
        
        # Pattern 8: Look for comparison winner patterns
        # "X emerges as the clear winner" or "X is the stronger candidate"
        winner_patterns = [
            r'\*\*([^*]+)\*\*[^.]*(?:emerges as the (?:clear )?winner|is the (?:stronger|better) candidate|wins the comparison)',
            r'(?:the\s+)?winner\s+is\s+\*\*([^*]+)\*\*',
            r'\*\*([^*]+)\*\*[^.]*(?:has the edge|comes out on top|is the winner)'
        ]
        for pattern in winner_patterns:
            winner_match = re.search(pattern, content, re.IGNORECASE)
            if winner_match:
                name = winner_match.group(1).strip()
                cv_id = _extract_cv_id_for_name(content, name)
                if cv_id:
                    logger.info(f"[CONTEXT_RESOLVER] Found comparison winner: {name} ({cv_id})")
                    return {"name": name, "cv_id": cv_id}
        
        # Pattern 9: Fallback - First CV link in ranking response (the #1 candidate is typically listed first)
        # Look for pattern like [📄](cv:cv_xxx) **Name** with score
        first_cv_link = re.search(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*',
            content
        )
        if first_cv_link:
            cv_id = first_cv_link.group(1).strip()
            name = first_cv_link.group(2).strip()
            logger.info(f"[CONTEXT_RESOLVER] Found first CV link (likely #1): {name} ({cv_id})")
            return {"name": name, "cv_id": cv_id}
    
    logger.warning("[CONTEXT_RESOLVER] Could not find candidate in history")
    return None


def _extract_previous_results(
    conversation_history: List[Dict[str, str]]
) -> Optional[List[Dict[str, str]]]:
    """
    PHASE 5.4: Extract all candidates mentioned in the previous response.
    
    Used for follow-up questions like "tell me more about those candidates".
    """
    logger.info("[CONTEXT_RESOLVER] Extracting candidates from previous results")
    
    for msg in reversed(conversation_history):
        if msg.get("role") != "assistant":
            continue
        
        content = msg.get("content", "")
        
        # Find all CV links in the response
        all_matches = re.findall(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*',
            content
        )
        
        if all_matches:
            candidates = []
            seen_ids = set()
            for cv_id, name in all_matches:
                if cv_id not in seen_ids:
                    candidates.append({"name": name.strip(), "cv_id": cv_id.strip()})
                    seen_ids.add(cv_id)
            
            if candidates:
                logger.info(f"[CONTEXT_RESOLVER] Found {len(candidates)} candidates from previous results")
                return candidates
    
    return None


def _extract_senior_candidate(
    conversation_history: List[Dict[str, str]]
) -> Optional[Dict[str, str]]:
    """
    PHASE 5.4: Extract senior-level candidate from history.
    
    Looks for candidates marked as "Senior" or with high experience.
    """
    logger.info("[CONTEXT_RESOLVER] Looking for senior candidate")
    
    for msg in reversed(conversation_history):
        if msg.get("role") != "assistant":
            continue
        
        content = msg.get("content", "")
        
        # Look for "Senior" badge near a candidate
        senior_match = re.search(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*[^<\n]*(?:Senior|Principal|Lead)',
            content,
            re.IGNORECASE
        )
        if senior_match:
            cv_id = senior_match.group(1).strip()
            name = senior_match.group(2).strip()
            logger.info(f"[CONTEXT_RESOLVER] Found senior candidate: {name}")
            return {"name": name, "cv_id": cv_id}
        
        # Fallback: Look for highest experience candidate
        exp_matches = re.findall(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*[^0-9]*(\d+)\s*(?:years?|yrs)',
            content,
            re.IGNORECASE
        )
        if exp_matches:
            best = max(exp_matches, key=lambda x: int(x[2]))
            cv_id = best[0].strip()
            name = best[1].strip()
            logger.info(f"[CONTEXT_RESOLVER] Found most experienced candidate: {name} ({best[2]} yrs)")
            return {"name": name, "cv_id": cv_id}
    
    return None


def _extract_top_candidates_from_history(
    conversation_history: List[Dict[str, str]]
) -> Optional[List[Dict[str, str]]]:
    """
    Extract top 2 candidates from ranking history.
    
    Used for "compare the two best" queries.
    
    Args:
        conversation_history: Previous messages
        
    Returns:
        List of 2 dicts with "name" and "cv_id" if found, None otherwise
    """
    logger.info("[CONTEXT_RESOLVER] Extracting top 2 candidates for comparison")
    
    # Look through history from most recent to oldest
    for idx, msg in enumerate(reversed(conversation_history)):
        if msg.get("role") != "assistant":
            continue
        
        content = msg.get("content", "")
        
        # Look for ranking with scores
        ranking_matches = re.findall(
            r'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*[^0-9]*([0-9]+)%',
            content
        )
        if ranking_matches and len(ranking_matches) >= 2:
            # Sort by score descending and take top 2
            sorted_matches = sorted(ranking_matches, key=lambda x: int(x[2]), reverse=True)[:2]
            
            top_candidates = []
            for cv_id, name, score in sorted_matches:
                top_candidates.append({
                    "name": name.strip(),
                    "cv_id": cv_id.strip(),
                    "score": int(score)
                })
            
            logger.info(f"[CONTEXT_RESOLVER] Found top 2: {[c['name'] for c in top_candidates]}")
            return top_candidates
    
    logger.warning("[CONTEXT_RESOLVER] Could not find 2 candidates in history")
    return None


def _extract_cv_id_for_name(content: str, name: str) -> Optional[str]:
    """Extract cv_id for a given candidate name from content."""
    # Clean the name for matching (remove extra suffixes like "Business", "Graduate", etc.)
    name_parts = name.split()
    # Use first two parts as core name (first + last name)
    core_name = ' '.join(name_parts[:2]) if len(name_parts) >= 2 else name
    
    # Pattern 1: **[Name](cv:cv_xxx)** - exact markdown link format
    pattern1 = rf'\*\*\[{re.escape(name)}[^\]]*\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*'
    match = re.search(pattern1, content, re.IGNORECASE)
    if match:
        logger.info(f"[CONTEXT_RESOLVER] Found cv_id via exact link: {match.group(1)}")
        return match.group(1)
    
    # Pattern 2: Try with core name (first + last only)
    if core_name != name:
        pattern2 = rf'\*\*\[{re.escape(core_name)}[^\]]*\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*'
        match = re.search(pattern2, content, re.IGNORECASE)
        if match:
            logger.info(f"[CONTEXT_RESOLVER] Found cv_id via core name link: {match.group(1)}")
            return match.group(1)
    
    # Pattern 3: [📄](cv:cv_xxx) **Name** - icon link format
    pattern3 = rf'\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*{re.escape(core_name)}'
    match = re.search(pattern3, content, re.IGNORECASE)
    if match:
        logger.info(f"[CONTEXT_RESOLVER] Found cv_id via icon link: {match.group(1)}")
        return match.group(1)
    
    # Pattern 4: Look for cv_id immediately before or after the name (within 50 chars)
    name_pos = content.lower().find(core_name.lower())
    if name_pos != -1:
        # Search within 50 chars (tighter range to avoid wrong candidate)
        search_area = content[max(0, name_pos-50):min(len(content), name_pos+len(core_name)+50)]
        cv_match = re.search(r'cv:(cv_[a-zA-Z0-9_-]+)', search_area)
        if cv_match:
            logger.info(f"[CONTEXT_RESOLVER] Found cv_id near name: {cv_match.group(1)}")
            return cv_match.group(1)
    
    logger.warning(f"[CONTEXT_RESOLVER] Could not find cv_id for: {name}")
    return None


def resolve_reference(
    query: str,
    conversation_history: List[Dict[str, str]]
) -> ResolvedReference:
    """
    Main entry point: Resolve any reference in the query using conversation history.
    
    Args:
        query: User's current query
        conversation_history: Previous messages
        
    Returns:
        ResolvedReference with resolved candidate info
    """
    # Check if query has a reference pattern
    has_ref, ref_type = has_reference_pattern(query)
    
    if not has_ref:
        return ResolvedReference(resolved=False, reference_type="none")
    
    logger.info(f"[CONTEXT_RESOLVER] Detected reference pattern: {ref_type}")
    
    # Try to extract candidate from history
    candidate = extract_candidate_from_history(conversation_history, ref_type)
    
    if candidate:
        # Handle multiple candidates case
        if ref_type == "top_candidates" and isinstance(candidate, list):
            return ResolvedReference(
                resolved=True,
                candidate_name=f"Top 2: {', '.join([c['name'] for c in candidate])}",
                cv_id=candidate[0].get("cv_id") if candidate else None,  # Primary candidate
                reference_type=ref_type,
                confidence=0.85
            )
        else:
            return ResolvedReference(
                resolved=True,
                candidate_name=candidate.get("name"),
                cv_id=candidate.get("cv_id"),
                reference_type=ref_type,
                confidence=0.85
            )
    
    return ResolvedReference(
        resolved=False,
        reference_type=ref_type,
        confidence=0.0
    )


def resolve_query_with_context(
    query: str,
    conversation_history: List[Dict[str, str]]
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Resolve a query by replacing references with actual candidate names.
    
    Args:
        query: Original query with potential references
        conversation_history: Previous messages
        
    Returns:
        Tuple of (resolved_query, candidate_name, cv_id)
    """
    # Debug: Log conversation history summary
    if conversation_history:
        logger.info(f"[CONTEXT_RESOLVER] Conversation history has {len(conversation_history)} messages")
        for i, msg in enumerate(conversation_history[-4:]):  # Last 4 messages
            role = msg.get("role", "?")
            content = msg.get("content", "")[:200]
            logger.info(f"[CONTEXT_RESOLVER] History[{i}] {role}: {content}...")
    else:
        logger.warning("[CONTEXT_RESOLVER] No conversation history provided!")
    
    resolution = resolve_reference(query, conversation_history)
    
    if not resolution.resolved or not resolution.candidate_name:
        logger.info(f"[CONTEXT_RESOLVER] No resolution found for query: {query}")
        return query, None, None
    
    # Replace reference patterns with the actual name
    resolved_query = query
    name = resolution.candidate_name
    
    replacements = [
        # #1 candidate patterns
        (r'#1\s*candidate', name),
        (r'#1\s*candidato', name),
        (r'(the\s+)?#1\b', name),
        (r'full\s+profile\s+of\s+(the\s+)?#\d+\s*(candidate)?', f'full profile of {name}'),
        (r'profile\s+of\s+(the\s+)?#\d+', f'profile of {name}'),
        # Top/best candidate patterns
        (r'\b(the\s+)?top\s+candidate\b', name),
        (r'\b(el\s+)?top\s+candidate\b', name),
        (r'\b(el\s+)?(mejor|best)\s+(candidato|candidate)\b', name),
        (r'\b(the\s+)?best\s+one\b', name),
        (r'\b(the\s+)?first\s+candidate\b', name),
        (r'\b(the\s+)?first\s+one\b', name),
        # This/that patterns
        (r'\b(this|that|ese|este|esta)\s+(candidato|candidate|person|persona)\b', name),
    ]
    
    for pattern, replacement in replacements:
        resolved_query = re.sub(pattern, replacement, resolved_query, flags=re.IGNORECASE)
    
    logger.info(f"[CONTEXT_RESOLVER] Resolved '{query}' -> '{resolved_query}' (candidate: {name})")
    
    return resolved_query, resolution.candidate_name, resolution.cv_id
