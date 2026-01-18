"""
QUERY ANALYZER - Intelligent Query Understanding for Adaptive System

Analyzes queries to understand:
1. WHAT the user is asking about (attributes, entities)
2. HOW they want the data presented (format hints)
3. WHICH candidates/scope they're interested in
4. WHAT operations to perform (list, count, compare, rank)

This is the FIRST step in the adaptive pipeline - understanding intent.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """High-level intent categories."""
    LIST_ATTRIBUTE = "list_attribute"      # "What skills do candidates have?"
    COUNT_ATTRIBUTE = "count_attribute"    # "How many candidates know Python?"
    DISTRIBUTION = "distribution"          # "What's the distribution of skills?"
    FIND_BY_ATTRIBUTE = "find_by_attr"     # "Who knows React?"
    COMPARE_ATTRIBUTE = "compare_attr"     # "Compare experience levels"
    AGGREGATE = "aggregate"                # "Average years of experience"
    UNKNOWN = "unknown"


class DataFormat(Enum):
    """Suggested output format based on query."""
    CANDIDATE_ROWS = "candidate_rows"      # Rows = candidates, Cols = attributes
    ATTRIBUTE_ROWS = "attribute_rows"      # Rows = attributes, Cols = stats
    MATRIX = "matrix"                      # Candidate × Attribute grid
    RANKED_LIST = "ranked_list"            # Ordered by some criteria
    GROUPED = "grouped"                    # Grouped by attribute value


@dataclass
class DetectedAttribute:
    """An attribute detected from the query."""
    name: str                              # Normalized name (e.g., "skills")
    original_term: str                     # Original term from query
    metadata_keys: List[str]               # Keys to look for in chunk metadata
    content_patterns: List[str]            # Regex patterns to find in content
    priority: int = 1                      # Higher = more important


@dataclass
class QueryAnalysis:
    """Complete analysis of a query."""
    original_query: str
    intent: QueryIntent
    suggested_format: DataFormat
    detected_attributes: List[DetectedAttribute]
    scope: str                             # "all", "filtered", "specific"
    sort_preference: Optional[str]         # "alphabetical", "frequency", "score"
    limit_hint: Optional[int]              # If user asked for "top 5" etc.
    aggregation: Optional[str]             # "count", "average", "sum", etc.
    filter_conditions: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class QueryAnalyzer:
    """
    Intelligent query analyzer that understands user intent dynamically.
    
    Unlike rigid pattern matching, this analyzer:
    - Extracts multiple possible attributes
    - Infers the best output format
    - Detects scope and filters
    - Handles ambiguous queries gracefully
    """
    
    # Attribute knowledge base - maps concepts to metadata keys and patterns
    ATTRIBUTE_KNOWLEDGE = {
        "technologies": {
            "aliases": ["technology", "technologies", "tech", "tech stack", "programming"],
            "metadata_keys": ["skills", "technologies", "tech_stack"],
            "content_patterns": [
                r'\b(Python|Java|JavaScript|TypeScript|React|Angular|Vue|Node\.?js|'
                r'AWS|Azure|GCP|Docker|Kubernetes|SQL|NoSQL|MongoDB|PostgreSQL|'
                r'Redis|GraphQL|REST|API|Git|CI/CD|Jenkins|Terraform)\b'
            ],
            "priority": 1
        },
        "skills": {
            "aliases": ["skill", "skills", "abilities", "competencies", "expertise"],
            "metadata_keys": ["skills", "competencies", "abilities"],
            "content_patterns": [r'\b(?:skilled in|proficient in|expert in|knowledge of)\s+([^,.\n]+)'],
            "priority": 1
        },
        "languages": {
            "aliases": ["language", "languages", "speaks", "spoken", "idiomas"],
            "metadata_keys": ["languages", "spoken_languages", "language_skills"],
            "content_patterns": [
                r'\b(English|Spanish|French|German|Chinese|Japanese|Korean|'
                r'Portuguese|Italian|Russian|Arabic|Hindi|Dutch)\b'
            ],
            "priority": 2
        },
        "experience": {
            "aliases": ["experience", "years", "tenure", "work history", "experiencia"],
            "metadata_keys": ["total_experience_years", "experience_years", "years_experience"],
            "content_patterns": [r'(\d+)\+?\s*(?:years?|años?)'],
            "priority": 2
        },
        "education": {
            "aliases": ["education", "degree", "university", "studies", "estudios", "graduated"],
            "metadata_keys": ["education", "degree", "university", "qualification"],
            "content_patterns": [
                r'\b(Bachelor|Master|PhD|MBA|BSc|MSc|BA|MA|Doctorate|'
                r'Universidad|University|College|Institute)\b'
            ],
            "priority": 3
        },
        "certifications": {
            "aliases": ["certification", "certifications", "certified", "certificate", "credentials"],
            "metadata_keys": ["certifications", "certificates", "credentials"],
            "content_patterns": [
                r'\b(AWS Certified|Google Cloud|Azure|PMP|Scrum Master|'
                r'CISSP|CPA|CFA|Six Sigma|ITIL)\b'
            ],
            "priority": 3
        },
        "location": {
            "aliases": ["location", "located", "based", "city", "country", "ubicación"],
            "metadata_keys": ["location", "city", "country", "region"],
            "content_patterns": [r'\b(?:based in|located in|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'],
            "priority": 4
        },
        "role": {
            "aliases": ["role", "position", "job", "title", "puesto", "cargo"],
            "metadata_keys": ["current_role", "job_title", "position", "role"],
            "content_patterns": [
                r'\b(Developer|Engineer|Manager|Director|Analyst|Designer|'
                r'Architect|Lead|Senior|Junior|Principal|VP|CEO|CTO)\b'
            ],
            "priority": 2
        },
        "seniority": {
            "aliases": ["seniority", "level", "senior", "junior", "mid-level"],
            "metadata_keys": ["seniority_level", "level", "seniority"],
            "content_patterns": [r'\b(Junior|Mid|Senior|Lead|Principal|Staff|Director)\b'],
            "priority": 3
        },
        "company": {
            "aliases": ["company", "companies", "employer", "worked at", "empresa"],
            "metadata_keys": ["company", "companies", "employer", "organization"],
            "content_patterns": [r'\bat\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+(?:as|from|since)|[,.]|$)'],
            "priority": 4
        }
    }
    
    # Intent detection patterns
    INTENT_PATTERNS = {
        QueryIntent.LIST_ATTRIBUTE: [
            r'\bwhat\s+(?:\w+\s+)*(?:do|does|are)\s+',
            r'\blist\s+(?:all\s+)?',
            r'\bshow\s+(?:me\s+)?(?:all\s+)?',
            r'\btell\s+me\s+(?:about\s+)?',
        ],
        QueryIntent.COUNT_ATTRIBUTE: [
            r'\bhow\s+many\b',
            r'\bcount\s+',
            r'\bnumber\s+of\b',
            r'\bcuántos\b',
        ],
        QueryIntent.DISTRIBUTION: [
            r'\bdistribution\b',
            r'\bbreakdown\b',
            r'\bspread\b',
            r'\bpercentage\b',
        ],
        QueryIntent.FIND_BY_ATTRIBUTE: [
            r'\bwho\s+(?:has|have|knows?|speaks?)\b',
            r'\bfind\s+(?:candidates?\s+)?(?:with|who)\b',
            r'\bquién\s+',
        ],
        QueryIntent.COMPARE_ATTRIBUTE: [
            r'\bcompare\b',
            r'\bdifference\b',
            r'\bvs\b',
        ],
        QueryIntent.AGGREGATE: [
            r'\baverage\b',
            r'\btotal\b',
            r'\bsum\b',
            r'\bmin(?:imum)?\b',
            r'\bmax(?:imum)?\b',
        ],
    }
    
    # Format hints from query
    FORMAT_HINTS = {
        DataFormat.RANKED_LIST: [r'\btop\s+\d+', r'\bbest\b', r'\branked\b', r'\bordered\b'],
        DataFormat.GROUPED: [r'\bgroup(?:ed)?\s+by\b', r'\bby\s+\w+\b', r'\bper\s+\w+\b'],
        DataFormat.ATTRIBUTE_ROWS: [r'\bdistribution\b', r'\bbreakdown\b', r'\bfrequency\b'],
    }
    
    def analyze(self, query: str, chunks: List[Dict[str, Any]] = None) -> QueryAnalysis:
        """
        Analyze a query to understand intent and extract attributes.
        
        Args:
            query: User's natural language query
            chunks: Optional chunks for context-aware analysis
            
        Returns:
            QueryAnalysis with all detected information
        """
        q_lower = query.lower()
        
        # 1. Detect intent
        intent = self._detect_intent(q_lower)
        logger.info(f"[QUERY_ANALYZER] Detected intent: {intent.value}")
        
        # 2. Detect attributes mentioned in query
        attributes = self._detect_attributes(q_lower, chunks)
        logger.info(f"[QUERY_ANALYZER] Detected attributes: {[a.name for a in attributes]}")
        
        # 3. Infer best format
        suggested_format = self._infer_format(q_lower, intent, attributes)
        logger.info(f"[QUERY_ANALYZER] Suggested format: {suggested_format.value}")
        
        # 4. Detect scope and filters
        scope = self._detect_scope(q_lower)
        limit_hint = self._detect_limit(q_lower)
        sort_preference = self._detect_sort_preference(q_lower, intent)
        aggregation = self._detect_aggregation(q_lower)
        filters = self._detect_filters(q_lower, attributes)
        
        # 5. Calculate confidence
        confidence = self._calculate_confidence(intent, attributes)
        
        return QueryAnalysis(
            original_query=query,
            intent=intent,
            suggested_format=suggested_format,
            detected_attributes=attributes,
            scope=scope,
            sort_preference=sort_preference,
            limit_hint=limit_hint,
            aggregation=aggregation,
            filter_conditions=filters,
            confidence=confidence
        )
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect the primary intent of the query."""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return intent
        return QueryIntent.LIST_ATTRIBUTE  # Default to listing
    
    def _detect_attributes(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]] = None
    ) -> List[DetectedAttribute]:
        """Detect which attributes the user is asking about."""
        detected = []
        
        for attr_name, config in self.ATTRIBUTE_KNOWLEDGE.items():
            # Check if any alias is mentioned in query
            for alias in config["aliases"]:
                if alias.lower() in query:
                    detected.append(DetectedAttribute(
                        name=attr_name,
                        original_term=alias,
                        metadata_keys=config["metadata_keys"],
                        content_patterns=config["content_patterns"],
                        priority=config["priority"]
                    ))
                    break  # Don't add same attribute twice
        
        # If nothing detected, try to infer from chunks metadata
        if not detected and chunks:
            available_keys = self._get_available_metadata_keys(chunks)
            for attr_name, config in self.ATTRIBUTE_KNOWLEDGE.items():
                for key in config["metadata_keys"]:
                    if key in available_keys:
                        detected.append(DetectedAttribute(
                            name=attr_name,
                            original_term=attr_name,
                            metadata_keys=config["metadata_keys"],
                            content_patterns=config["content_patterns"],
                            priority=config["priority"]
                        ))
                        break
        
        # Default to skills if still nothing
        if not detected:
            config = self.ATTRIBUTE_KNOWLEDGE["skills"]
            detected.append(DetectedAttribute(
                name="skills",
                original_term="skills",
                metadata_keys=config["metadata_keys"],
                content_patterns=config["content_patterns"],
                priority=1
            ))
        
        # Sort by priority
        detected.sort(key=lambda x: x.priority)
        
        return detected
    
    def _get_available_metadata_keys(self, chunks: List[Dict[str, Any]]) -> Set[str]:
        """Get all unique metadata keys from chunks."""
        keys = set()
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            keys.update(meta.keys())
        return keys
    
    def _infer_format(
        self, 
        query: str, 
        intent: QueryIntent, 
        attributes: List[DetectedAttribute]
    ) -> DataFormat:
        """Infer the best output format based on query and intent."""
        # Check for explicit format hints
        for fmt, patterns in self.FORMAT_HINTS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return fmt
        
        # Infer from intent
        if intent == QueryIntent.DISTRIBUTION:
            return DataFormat.ATTRIBUTE_ROWS
        elif intent == QueryIntent.COUNT_ATTRIBUTE:
            return DataFormat.ATTRIBUTE_ROWS
        elif intent == QueryIntent.FIND_BY_ATTRIBUTE:
            return DataFormat.CANDIDATE_ROWS
        elif intent == QueryIntent.COMPARE_ATTRIBUTE:
            return DataFormat.MATRIX
        
        # Default based on number of attributes
        if len(attributes) > 2:
            return DataFormat.MATRIX
        
        return DataFormat.CANDIDATE_ROWS
    
    def _detect_scope(self, query: str) -> str:
        """Detect the scope of the query."""
        if re.search(r'\ball\s+candidates?\b', query):
            return "all"
        elif re.search(r'\b(the|this|that)\s+candidate\b', query):
            return "specific"
        elif re.search(r'\b(some|few|certain)\s+candidates?\b', query):
            return "filtered"
        return "all"
    
    def _detect_limit(self, query: str) -> Optional[int]:
        """Detect if user wants a limited number of results."""
        match = re.search(r'\btop\s+(\d+)\b', query, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        match = re.search(r'\b(\d+)\s+(?:best|top|first)\b', query, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None
    
    def _detect_sort_preference(self, query: str, intent: QueryIntent) -> Optional[str]:
        """Detect how results should be sorted."""
        if re.search(r'\balphabetical(?:ly)?\b', query):
            return "alphabetical"
        elif re.search(r'\bfrequen(?:cy|t)\b', query):
            return "frequency"
        elif re.search(r'\b(?:score|relevance|match)\b', query):
            return "score"
        elif re.search(r'\b(?:experience|years)\b', query):
            return "experience"
        
        # Default based on intent
        if intent == QueryIntent.DISTRIBUTION:
            return "frequency"
        elif intent == QueryIntent.LIST_ATTRIBUTE:
            return "score"
        
        return None
    
    def _detect_aggregation(self, query: str) -> Optional[str]:
        """Detect if an aggregation operation is requested."""
        if re.search(r'\baverage\b', query):
            return "average"
        elif re.search(r'\btotal\b', query):
            return "sum"
        elif re.search(r'\bcount\b', query):
            return "count"
        elif re.search(r'\bmin(?:imum)?\b', query):
            return "min"
        elif re.search(r'\bmax(?:imum)?\b', query):
            return "max"
        return None
    
    def _detect_filters(
        self, 
        query: str, 
        attributes: List[DetectedAttribute]
    ) -> Dict[str, Any]:
        """Detect filter conditions in the query."""
        filters = {}
        
        # Detect "with X" patterns
        match = re.search(r'\bwith\s+([^,.\n]+?)(?:\s+(?:and|or|experience|skills)|$)', query)
        if match:
            filters["must_have"] = match.group(1).strip()
        
        # Detect "without X" patterns
        match = re.search(r'\bwithout\s+([^,.\n]+?)(?:\s+(?:and|or)|$)', query)
        if match:
            filters["must_not_have"] = match.group(1).strip()
        
        # Detect experience thresholds
        match = re.search(r'(\d+)\+?\s*(?:years?|años?)\s*(?:of\s+)?experience', query)
        if match:
            filters["min_experience"] = int(match.group(1))
        
        return filters
    
    def _calculate_confidence(
        self, 
        intent: QueryIntent, 
        attributes: List[DetectedAttribute]
    ) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.5  # Base
        
        # Higher confidence if we detected clear intent
        if intent != QueryIntent.UNKNOWN:
            confidence += 0.2
        
        # Higher confidence if we detected attributes
        if attributes:
            confidence += 0.1 * min(len(attributes), 3)
        
        return min(confidence, 1.0)
