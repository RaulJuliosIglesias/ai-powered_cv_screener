"""
Candidate Scoring Service - Configurable 0-100 scoring system.

V8 Feature: Calculate weighted scores for candidates based on job requirements.
Allows customizing weights for different criteria.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ScoringCriteria(Enum):
    """Criteria for scoring candidates."""
    SKILLS_MATCH = "skills_match"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    RELEVANCE = "relevance"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    LOCATION = "location"
    CULTURAL_FIT = "cultural_fit"
    CUSTOM = "custom"


@dataclass
class CriteriaWeight:
    """Weight configuration for a scoring criterion."""
    criteria: ScoringCriteria
    weight: float  # 0.0 to 1.0
    max_points: int = 100
    required: bool = False
    custom_scorer: Optional[str] = None  # For CUSTOM criteria
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "criteria": self.criteria.value,
            "weight": self.weight,
            "max_points": self.max_points,
            "required": self.required
        }


@dataclass
class CriteriaScore:
    """Score for a single criterion."""
    criteria: ScoringCriteria
    raw_score: float  # 0-100
    weighted_score: float
    weight: float
    details: Optional[str] = None
    matched_items: List[str] = field(default_factory=list)


@dataclass
class CandidateScore:
    """Complete score for a candidate."""
    candidate_id: str
    candidate_name: str
    total_score: float  # 0-100
    grade: str  # A, B, C, D, F
    criteria_scores: List[CriteriaScore] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "total_score": round(self.total_score, 1),
            "grade": self.grade,
            "criteria_scores": [
                {
                    "criteria": cs.criteria.value,
                    "raw_score": round(cs.raw_score, 1),
                    "weighted_score": round(cs.weighted_score, 2),
                    "weight": cs.weight,
                    "details": cs.details,
                    "matched_items": cs.matched_items
                }
                for cs in self.criteria_scores
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendation": self.recommendation
        }


@dataclass
class ScoringProfile:
    """A scoring profile with customized weights."""
    id: str
    name: str
    weights: List[CriteriaWeight] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    min_experience_years: float = 0
    ideal_experience_years: float = 5
    required_education: Optional[str] = None
    preferred_locations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "weights": [w.to_dict() for w in self.weights],
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "min_experience_years": self.min_experience_years,
            "ideal_experience_years": self.ideal_experience_years,
            "required_education": self.required_education,
            "preferred_locations": self.preferred_locations
        }


# Default weights
DEFAULT_WEIGHTS = [
    CriteriaWeight(ScoringCriteria.SKILLS_MATCH, weight=0.35, required=True),
    CriteriaWeight(ScoringCriteria.EXPERIENCE, weight=0.25),
    CriteriaWeight(ScoringCriteria.RELEVANCE, weight=0.20),
    CriteriaWeight(ScoringCriteria.EDUCATION, weight=0.10),
    CriteriaWeight(ScoringCriteria.CERTIFICATIONS, weight=0.05),
    CriteriaWeight(ScoringCriteria.LANGUAGES, weight=0.05),
]


class CandidateScoringService:
    """Service for scoring candidates based on job requirements."""
    
    def __init__(self):
        self._profiles: Dict[str, ScoringProfile] = {}
        self._session_profiles: Dict[str, str] = {}  # session_id -> profile_id
    
    def create_profile(
        self,
        name: str,
        weights: Optional[List[Dict[str, Any]]] = None,
        required_skills: List[str] = None,
        preferred_skills: List[str] = None,
        min_experience: float = 0,
        ideal_experience: float = 5,
        required_education: Optional[str] = None,
        preferred_locations: List[str] = None
    ) -> ScoringProfile:
        """Create a scoring profile."""
        import uuid
        profile_id = str(uuid.uuid4())[:8]
        
        # Parse weights or use defaults
        parsed_weights = []
        if weights:
            for w in weights:
                parsed_weights.append(CriteriaWeight(
                    criteria=ScoringCriteria(w["criteria"]),
                    weight=w["weight"],
                    max_points=w.get("max_points", 100),
                    required=w.get("required", False)
                ))
        else:
            parsed_weights = DEFAULT_WEIGHTS.copy()
        
        # Normalize weights to sum to 1.0
        total_weight = sum(w.weight for w in parsed_weights)
        if total_weight > 0:
            for w in parsed_weights:
                w.weight = w.weight / total_weight
        
        profile = ScoringProfile(
            id=profile_id,
            name=name,
            weights=parsed_weights,
            required_skills=required_skills or [],
            preferred_skills=preferred_skills or [],
            min_experience_years=min_experience,
            ideal_experience_years=ideal_experience,
            required_education=required_education,
            preferred_locations=preferred_locations or []
        )
        
        self._profiles[profile_id] = profile
        logger.info(f"[SCORING] Created profile '{name}' with {len(parsed_weights)} criteria")
        
        return profile
    
    def assign_to_session(self, session_id: str, profile_id: str) -> bool:
        """Assign a scoring profile to a session."""
        if profile_id not in self._profiles:
            return False
        self._session_profiles[session_id] = profile_id
        return True
    
    def score_candidate(
        self,
        candidate_data: Dict[str, Any],
        profile_id: Optional[str] = None,
        session_id: Optional[str] = None,
        query_context: Optional[str] = None
    ) -> CandidateScore:
        """Score a candidate against a profile.
        
        Args:
            candidate_data: Candidate information
            profile_id: Scoring profile to use
            session_id: Session to get assigned profile
            query_context: Optional query for relevance scoring
            
        Returns:
            CandidateScore with detailed breakdown
        """
        # Get profile
        if profile_id:
            profile = self._profiles.get(profile_id)
        elif session_id:
            assigned_id = self._session_profiles.get(session_id)
            profile = self._profiles.get(assigned_id) if assigned_id else None
        else:
            profile = None
        
        # Use default profile if none specified
        if not profile:
            profile = ScoringProfile(
                id="default",
                name="Default Profile",
                weights=DEFAULT_WEIGHTS.copy()
            )
        
        candidate_id = candidate_data.get("cv_id", candidate_data.get("id", "unknown"))
        candidate_name = candidate_data.get("name", candidate_data.get("candidate_name", "Unknown"))
        
        # Score each criterion
        criteria_scores = []
        for weight in profile.weights:
            score = self._score_criterion(weight, candidate_data, profile, query_context)
            criteria_scores.append(score)
        
        # Calculate total weighted score
        total_score = sum(cs.weighted_score for cs in criteria_scores)
        
        # Determine grade
        grade = self._calculate_grade(total_score)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._analyze_performance(criteria_scores)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(total_score, grade, strengths, weaknesses)
        
        return CandidateScore(
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            total_score=total_score,
            grade=grade,
            criteria_scores=criteria_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation
        )
    
    def _score_criterion(
        self,
        weight: CriteriaWeight,
        candidate: Dict[str, Any],
        profile: ScoringProfile,
        query_context: Optional[str]
    ) -> CriteriaScore:
        """Score a single criterion."""
        criteria = weight.criteria
        raw_score = 0.0
        details = ""
        matched_items = []
        
        if criteria == ScoringCriteria.SKILLS_MATCH:
            raw_score, details, matched_items = self._score_skills(candidate, profile)
            
        elif criteria == ScoringCriteria.EXPERIENCE:
            raw_score, details = self._score_experience(candidate, profile)
            
        elif criteria == ScoringCriteria.EDUCATION:
            raw_score, details = self._score_education(candidate, profile)
            
        elif criteria == ScoringCriteria.RELEVANCE:
            raw_score, details = self._score_relevance(candidate, query_context)
            
        elif criteria == ScoringCriteria.CERTIFICATIONS:
            raw_score, details, matched_items = self._score_certifications(candidate)
            
        elif criteria == ScoringCriteria.LANGUAGES:
            raw_score, details, matched_items = self._score_languages(candidate)
            
        elif criteria == ScoringCriteria.LOCATION:
            raw_score, details = self._score_location(candidate, profile)
        
        weighted_score = raw_score * weight.weight
        
        return CriteriaScore(
            criteria=criteria,
            raw_score=raw_score,
            weighted_score=weighted_score,
            weight=weight.weight,
            details=details,
            matched_items=matched_items
        )
    
    def _score_skills(
        self,
        candidate: Dict[str, Any],
        profile: ScoringProfile
    ) -> tuple:
        """Score skills match."""
        candidate_skills = candidate.get("skills", [])
        if isinstance(candidate_skills, str):
            candidate_skills = [s.strip().lower() for s in candidate_skills.split(",")]
        else:
            candidate_skills = [s.lower() for s in candidate_skills]
        
        # Check required skills
        required = profile.required_skills
        preferred = profile.preferred_skills
        
        if not required and not preferred:
            # No skills specified, give benefit of doubt based on skill count
            score = min(100, len(candidate_skills) * 10)
            return score, f"{len(candidate_skills)} skills found", candidate_skills[:5]
        
        matched_required = []
        matched_preferred = []
        
        for skill in required:
            skill_lower = skill.lower()
            if any(skill_lower in cs or cs in skill_lower for cs in candidate_skills):
                matched_required.append(skill)
        
        for skill in preferred:
            skill_lower = skill.lower()
            if any(skill_lower in cs or cs in skill_lower for cs in candidate_skills):
                matched_preferred.append(skill)
        
        # Calculate score
        required_score = 0
        if required:
            required_score = (len(matched_required) / len(required)) * 70  # 70% weight for required
        
        preferred_score = 0
        if preferred:
            preferred_score = (len(matched_preferred) / len(preferred)) * 30  # 30% weight for preferred
        
        total_score = required_score + preferred_score
        
        details = f"Required: {len(matched_required)}/{len(required)}, Preferred: {len(matched_preferred)}/{len(preferred)}"
        matched = matched_required + matched_preferred
        
        return total_score, details, matched
    
    def _score_experience(
        self,
        candidate: Dict[str, Any],
        profile: ScoringProfile
    ) -> tuple:
        """Score experience years."""
        years = candidate.get("experience_years", candidate.get("years_experience", 0))
        if years is None:
            years = 0
        
        min_years = profile.min_experience_years
        ideal_years = profile.ideal_experience_years
        
        if years < min_years:
            score = (years / min_years) * 50 if min_years > 0 else 50
            details = f"{years} years (minimum: {min_years})"
        elif years >= ideal_years:
            score = 100
            details = f"{years} years (ideal: {ideal_years}+)"
        else:
            # Between min and ideal
            range_size = ideal_years - min_years
            progress = (years - min_years) / range_size if range_size > 0 else 1
            score = 50 + (progress * 50)
            details = f"{years} years (range: {min_years}-{ideal_years})"
        
        return score, details
    
    def _score_education(
        self,
        candidate: Dict[str, Any],
        profile: ScoringProfile
    ) -> tuple:
        """Score education level."""
        education = candidate.get("education", candidate.get("education_summary", "")).lower()
        education_level = candidate.get("education_level", "").lower()
        
        # Education hierarchy
        levels = {
            "phd": 100,
            "doctorate": 100,
            "master": 85,
            "mba": 85,
            "bachelor": 70,
            "degree": 70,
            "associate": 55,
            "diploma": 50,
            "certificate": 40,
            "high school": 30
        }
        
        score = 30  # Base score
        detected_level = None
        
        for level, points in levels.items():
            if level in education or level in education_level:
                if points > score:
                    score = points
                    detected_level = level
        
        # Check if matches required education
        required = profile.required_education
        if required:
            required_lower = required.lower()
            if required_lower in education or required_lower in education_level:
                score = min(100, score + 10)
                details = f"Meets requirement: {required}"
            else:
                details = f"Education: {detected_level or 'unknown'} (required: {required})"
        else:
            details = f"Education level: {detected_level or 'detected'}"
        
        return score, details
    
    def _score_relevance(
        self,
        candidate: Dict[str, Any],
        query_context: Optional[str]
    ) -> tuple:
        """Score relevance to query context."""
        if not query_context:
            return 70, "No query context provided"
        
        # Use existing relevance score if available
        relevance = candidate.get("relevance_score", candidate.get("similarity", candidate.get("score")))
        if relevance is not None:
            score = float(relevance) * 100 if relevance <= 1 else relevance
            return score, f"Relevance score: {score:.1f}%"
        
        # Fallback: simple keyword matching
        content = candidate.get("content", candidate.get("full_text", "")).lower()
        query_terms = query_context.lower().split()
        
        matches = sum(1 for term in query_terms if term in content)
        match_ratio = matches / len(query_terms) if query_terms else 0
        
        score = match_ratio * 100
        return score, f"Matched {matches}/{len(query_terms)} query terms"
    
    def _score_certifications(self, candidate: Dict[str, Any]) -> tuple:
        """Score certifications."""
        certs = candidate.get("certifications", [])
        if isinstance(certs, str):
            certs = [c.strip() for c in certs.split(",") if c.strip()]
        
        if not certs:
            return 50, "No certifications listed", []
        
        # More certs = higher score (diminishing returns)
        score = min(100, 50 + len(certs) * 15)
        details = f"{len(certs)} certification(s)"
        
        return score, details, certs[:5]
    
    def _score_languages(self, candidate: Dict[str, Any]) -> tuple:
        """Score language skills."""
        langs = candidate.get("languages", [])
        if isinstance(langs, str):
            langs = [l.strip() for l in langs.split(",") if l.strip()]
        
        if not langs:
            return 50, "Languages not specified", []
        
        # More languages = higher score
        score = min(100, 50 + len(langs) * 20)
        details = f"{len(langs)} language(s)"
        
        return score, details, langs
    
    def _score_location(
        self,
        candidate: Dict[str, Any],
        profile: ScoringProfile
    ) -> tuple:
        """Score location match."""
        location = candidate.get("location", candidate.get("city", "")).lower()
        
        if not profile.preferred_locations:
            return 80, "No location preference"
        
        for pref in profile.preferred_locations:
            if pref.lower() in location or location in pref.lower():
                return 100, f"Location match: {location}"
        
        return 60, f"Location: {location or 'unknown'}"
    
    def _calculate_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        return "F"
    
    def _analyze_performance(
        self,
        criteria_scores: List[CriteriaScore]
    ) -> tuple:
        """Identify strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        for cs in criteria_scores:
            if cs.raw_score >= 80:
                strengths.append(f"{cs.criteria.value}: {cs.details}")
            elif cs.raw_score < 60:
                weaknesses.append(f"{cs.criteria.value}: {cs.details}")
        
        return strengths[:3], weaknesses[:3]
    
    def _generate_recommendation(
        self,
        score: float,
        grade: str,
        strengths: List[str],
        weaknesses: List[str]
    ) -> str:
        """Generate hiring recommendation."""
        if grade == "A":
            return "Highly recommended - Strong candidate matching most requirements"
        elif grade == "B":
            return "Recommended - Good candidate with minor gaps"
        elif grade == "C":
            return "Consider - Average match, review specific requirements"
        elif grade == "D":
            return "Weak match - Significant gaps in requirements"
        return "Not recommended - Does not meet key requirements"
    
    def get_profile(self, profile_id: str) -> Optional[ScoringProfile]:
        """Get a scoring profile."""
        return self._profiles.get(profile_id)
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all scoring profiles."""
        return [p.to_dict() for p in self._profiles.values()]
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete a scoring profile."""
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            return True
        return False


# Singleton instance
_scoring_service: Optional[CandidateScoringService] = None


def get_scoring_service() -> CandidateScoringService:
    """Get singleton scoring service instance."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = CandidateScoringService()
    return _scoring_service
