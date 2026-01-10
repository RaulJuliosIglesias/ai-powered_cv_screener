"""
V8 API Routes - Premium features endpoints.

Includes:
- Candidate Scoring
- Screening Rules
- Interview Questions
- Cache Stats
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Any
from pydantic import BaseModel

from app.config import settings, Mode
from app.models.sessions import session_manager
from app.providers.cloud.sessions import supabase_session_manager
from app.services.candidate_scoring_service import get_scoring_service
from app.services.screening_rules_service import get_screening_service
from app.services.interview_questions_service import get_interview_service
from app.services.semantic_cache_service import get_semantic_cache
from app.services.hybrid_search_service import get_hybrid_search_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v8", tags=["v8-premium"])


def get_session_manager(mode: Mode):
    """Get appropriate session manager based on mode."""
    if mode == Mode.CLOUD:
        return supabase_session_manager
    return session_manager


# ============================================================================
# Pydantic Models
# ============================================================================

class ScoringProfileCreate(BaseModel):
    name: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience: float = 0
    ideal_experience: float = 5
    required_education: Optional[str] = None
    preferred_locations: List[str] = []


class ScreeningRuleCreate(BaseModel):
    name: str
    field: str
    operator: str
    value: Any
    action: str
    priority: int = 0
    score_modifier: float = 0.0
    description: Optional[str] = None


class RuleSetCreate(BaseModel):
    name: str
    rules: List[ScreeningRuleCreate] = []
    require_all: bool = False


class CandidateData(BaseModel):
    cv_id: Optional[str] = None
    name: Optional[str] = None
    skills: List[str] = []
    experience_years: Optional[float] = None
    education: Optional[str] = None
    current_role: Optional[str] = None
    location: Optional[str] = None
    languages: List[str] = []
    certifications: List[str] = []


class InterviewRequest(BaseModel):
    candidate_data: CandidateData
    job_requirements: Optional[dict] = None
    num_questions: int = 10
    categories: Optional[List[str]] = None


# ============================================================================
# Candidate Scoring Endpoints
# ============================================================================

@router.post("/scoring/profiles")
async def create_scoring_profile(profile: ScoringProfileCreate):
    """Create a new scoring profile."""
    service = get_scoring_service()
    result = service.create_profile(
        name=profile.name,
        required_skills=profile.required_skills,
        preferred_skills=profile.preferred_skills,
        min_experience=profile.min_experience,
        ideal_experience=profile.ideal_experience,
        required_education=profile.required_education,
        preferred_locations=profile.preferred_locations
    )
    return {"profile_id": result.id, "name": result.name}


@router.get("/scoring/profiles")
async def list_scoring_profiles():
    """List all scoring profiles."""
    service = get_scoring_service()
    return {"profiles": service.list_profiles()}


@router.post("/scoring/score")
async def score_candidate(
    candidate: CandidateData,
    profile_id: Optional[str] = None,
    session_id: Optional[str] = None,
    query_context: Optional[str] = None
):
    """Score a candidate against a profile."""
    service = get_scoring_service()
    result = service.score_candidate(
        candidate_data=candidate.dict(),
        profile_id=profile_id,
        session_id=session_id,
        query_context=query_context
    )
    return result.to_dict()


@router.post("/scoring/session/{session_id}/assign")
async def assign_scoring_profile(
    session_id: str,
    profile_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Assign a scoring profile to a session."""
    service = get_scoring_service()
    success = service.assign_to_session(session_id, profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"success": True}


# ============================================================================
# Screening Rules Endpoints
# ============================================================================

@router.post("/screening/rule-sets")
async def create_rule_set(rule_set: RuleSetCreate):
    """Create a new screening rule set."""
    service = get_screening_service()
    rules_data = [r.dict() for r in rule_set.rules]
    result = service.create_rule_set(
        name=rule_set.name,
        rules=rules_data,
        require_all=rule_set.require_all
    )
    return {"rule_set_id": result.id, "name": result.name, "rules_count": len(result.rules)}


@router.get("/screening/rule-sets")
async def list_rule_sets():
    """List all screening rule sets."""
    service = get_screening_service()
    return {"rule_sets": service.list_rule_sets()}


@router.get("/screening/rule-sets/{rule_set_id}")
async def get_rule_set(rule_set_id: str):
    """Get a specific rule set."""
    service = get_screening_service()
    result = service.get_rule_set(rule_set_id)
    if not result:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return result.to_dict()


@router.post("/screening/rule-sets/{rule_set_id}/rules")
async def add_rule_to_set(rule_set_id: str, rule: ScreeningRuleCreate):
    """Add a rule to an existing rule set."""
    service = get_screening_service()
    result = service.add_rule(rule_set_id, rule.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return {"rule_id": result.id, "name": result.name}


@router.post("/screening/evaluate")
async def evaluate_candidate(
    candidate: CandidateData,
    rule_set_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Evaluate a candidate against screening rules."""
    service = get_screening_service()
    result = service.evaluate_candidate(
        candidate_data=candidate.dict(),
        rule_set_id=rule_set_id,
        session_id=session_id
    )
    return {
        "candidate_id": result.candidate_id,
        "candidate_name": result.candidate_name,
        "passed": result.passed,
        "score_modifier": result.score_modifier,
        "flags": result.flags,
        "exclusion_reason": result.exclusion_reason,
        "matched_rules_count": len([r for r in result.matched_rules if r.matched])
    }


@router.post("/screening/session/{session_id}/assign")
async def assign_rule_set(
    session_id: str,
    rule_set_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Assign a rule set to a session."""
    service = get_screening_service()
    success = service.assign_to_session(session_id, rule_set_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return {"success": True}


@router.delete("/screening/rule-sets/{rule_set_id}")
async def delete_rule_set(rule_set_id: str):
    """Delete a rule set."""
    service = get_screening_service()
    success = service.delete_rule_set(rule_set_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return {"success": True}


# ============================================================================
# Interview Questions Endpoints
# ============================================================================

@router.post("/interview/generate")
async def generate_interview_questions(request: InterviewRequest):
    """Generate tailored interview questions for a candidate."""
    service = get_interview_service()
    guide = service.generate_interview_guide(
        candidate_data=request.candidate_data.dict(),
        job_requirements=request.job_requirements,
        num_questions=request.num_questions,
        categories=request.categories
    )
    return guide.to_dict()


@router.get("/interview/categories")
async def list_question_categories():
    """List available question categories."""
    from app.services.interview_questions_service import QuestionCategory
    return {
        "categories": [
            {"id": cat.value, "name": cat.name.replace("_", " ").title()}
            for cat in QuestionCategory
        ]
    }


@router.post("/interview/single")
async def generate_single_question(
    category: str,
    skill: Optional[str] = None,
    experience: Optional[str] = None
):
    """Generate a single interview question."""
    service = get_interview_service()
    context = {}
    if skill:
        context["skill"] = skill
    if experience:
        context["experience"] = experience
    
    question = service.generate_single_question(category, context if context else None)
    return question.to_dict()


# ============================================================================
# Cache & Stats Endpoints
# ============================================================================

@router.get("/stats/cache")
async def get_cache_stats():
    """Get semantic cache statistics."""
    cache = get_semantic_cache()
    return cache.get_stats()


@router.post("/cache/invalidate/{session_id}")
async def invalidate_session_cache(session_id: str):
    """Invalidate cache for a specific session."""
    cache = get_semantic_cache()
    cache.invalidate_session(session_id)
    return {"success": True, "session_id": session_id}


@router.post("/cache/clear")
async def clear_all_cache():
    """Clear entire semantic cache."""
    cache = get_semantic_cache()
    cache.invalidate_all()
    return {"success": True}


@router.get("/stats/hybrid-search")
async def get_hybrid_search_stats():
    """Get hybrid search statistics."""
    service = get_hybrid_search_service()
    return service.get_stats()


@router.get("/stats/all")
async def get_all_v8_stats():
    """Get all V8 service statistics."""
    cache = get_semantic_cache()
    hybrid = get_hybrid_search_service()
    scoring = get_scoring_service()
    screening = get_screening_service()
    
    return {
        "semantic_cache": cache.get_stats(),
        "hybrid_search": hybrid.get_stats(),
        "scoring_profiles": len(scoring.list_profiles()),
        "screening_rule_sets": len(screening.list_rule_sets())
    }
