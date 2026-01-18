"""
Interview Questions Service - Generate tailored interview questions.

V8 Feature: Auto-generate interview questions based on candidate profile and job requirements.
Questions are tailored to explore specific skills, experience gaps, and verify claims.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QuestionCategory(Enum):
    """Categories of interview questions."""
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    EXPERIENCE_VERIFICATION = "experience_verification"
    SKILLS_DEEP_DIVE = "skills_deep_dive"
    CULTURAL_FIT = "cultural_fit"
    MOTIVATION = "motivation"
    LEADERSHIP = "leadership"
    PROBLEM_SOLVING = "problem_solving"
    GAP_EXPLORATION = "gap_exploration"


class QuestionDifficulty(Enum):
    """Difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class InterviewQuestion:
    """A single interview question."""
    id: str
    question: str
    category: QuestionCategory
    difficulty: QuestionDifficulty
    purpose: str  # Why ask this question
    follow_ups: List[str] = field(default_factory=list)
    expected_signals: List[str] = field(default_factory=list)  # What to look for in answer
    red_flags: List[str] = field(default_factory=list)  # Warning signs
    related_skill: Optional[str] = None
    time_estimate_minutes: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "purpose": self.purpose,
            "follow_ups": self.follow_ups,
            "expected_signals": self.expected_signals,
            "red_flags": self.red_flags,
            "related_skill": self.related_skill,
            "time_estimate_minutes": self.time_estimate_minutes
        }


@dataclass
class InterviewGuide:
    """Complete interview guide for a candidate."""
    candidate_id: str
    candidate_name: str
    questions: List[InterviewQuestion] = field(default_factory=list)
    total_time_minutes: int = 0
    focus_areas: List[str] = field(default_factory=list)
    areas_to_probe: List[str] = field(default_factory=list)
    strengths_to_confirm: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "questions": [q.to_dict() for q in self.questions],
            "total_time_minutes": self.total_time_minutes,
            "focus_areas": self.focus_areas,
            "areas_to_probe": self.areas_to_probe,
            "strengths_to_confirm": self.strengths_to_confirm
        }


# Question templates by category
QUESTION_TEMPLATES = {
    QuestionCategory.TECHNICAL: [
        {
            "template": "Can you explain how you would approach {skill} in a production environment?",
            "purpose": "Assess practical knowledge of {skill}",
            "follow_ups": [
                "What challenges have you faced with this?",
                "How do you handle edge cases?"
            ],
            "difficulty": QuestionDifficulty.MEDIUM
        },
        {
            "template": "Describe a complex {skill} problem you solved. Walk me through your approach.",
            "purpose": "Evaluate problem-solving with {skill}",
            "follow_ups": [
                "What alternatives did you consider?",
                "How would you improve your solution now?"
            ],
            "difficulty": QuestionDifficulty.HARD
        },
        {
            "template": "What are the key considerations when implementing {skill}?",
            "purpose": "Test fundamental understanding of {skill}",
            "follow_ups": ["Can you give an example?"],
            "difficulty": QuestionDifficulty.EASY
        }
    ],
    QuestionCategory.BEHAVIORAL: [
        {
            "template": "Tell me about a time when you had to learn {skill} quickly. How did you approach it?",
            "purpose": "Assess learning ability and adaptability",
            "follow_ups": [
                "What resources did you use?",
                "How long did it take to become proficient?"
            ],
            "difficulty": QuestionDifficulty.MEDIUM
        },
        {
            "template": "Describe a situation where you disagreed with a technical decision. How did you handle it?",
            "purpose": "Evaluate communication and conflict resolution",
            "follow_ups": ["What was the outcome?"],
            "difficulty": QuestionDifficulty.MEDIUM
        },
        {
            "template": "Tell me about a project that failed. What did you learn?",
            "purpose": "Assess self-awareness and growth mindset",
            "follow_ups": ["What would you do differently?"],
            "difficulty": QuestionDifficulty.HARD
        }
    ],
    QuestionCategory.EXPERIENCE_VERIFICATION: [
        {
            "template": "You mentioned {experience} on your CV. Can you elaborate on your specific role and contributions?",
            "purpose": "Verify claimed experience with {experience}",
            "follow_ups": [
                "What was the team size?",
                "What were the key metrics/outcomes?"
            ],
            "difficulty": QuestionDifficulty.EASY
        },
        {
            "template": "Walk me through a typical day in your role at {company}.",
            "purpose": "Verify depth of experience at {company}",
            "follow_ups": ["What tools did you use daily?"],
            "difficulty": QuestionDifficulty.EASY
        }
    ],
    QuestionCategory.GAP_EXPLORATION: [
        {
            "template": "I noticed you don't have experience with {skill}. How would you approach learning it?",
            "purpose": "Assess ability to fill skill gap in {skill}",
            "follow_ups": [
                "Have you worked with similar technologies?",
                "What timeline would you need?"
            ],
            "difficulty": QuestionDifficulty.MEDIUM
        },
        {
            "template": "Your experience seems focused on {area}. How do you see yourself transitioning to {target_area}?",
            "purpose": "Evaluate career transition plan",
            "follow_ups": ["What steps have you taken?"],
            "difficulty": QuestionDifficulty.MEDIUM
        }
    ],
    QuestionCategory.PROBLEM_SOLVING: [
        {
            "template": "How would you design a system for {scenario}?",
            "purpose": "Assess system design and architecture thinking",
            "follow_ups": [
                "How would you handle scale?",
                "What about failure scenarios?"
            ],
            "difficulty": QuestionDifficulty.HARD
        },
        {
            "template": "If you encountered a bug in production affecting {scenario}, how would you approach debugging?",
            "purpose": "Evaluate debugging methodology",
            "follow_ups": ["How would you prevent this in the future?"],
            "difficulty": QuestionDifficulty.MEDIUM
        }
    ],
    QuestionCategory.MOTIVATION: [
        {
            "template": "What attracted you to this role and our company?",
            "purpose": "Assess motivation and research done",
            "follow_ups": ["What excites you most about this opportunity?"],
            "difficulty": QuestionDifficulty.EASY
        },
        {
            "template": "Where do you see yourself in 3-5 years?",
            "purpose": "Understand career goals and alignment",
            "follow_ups": ["How does this role fit into that plan?"],
            "difficulty": QuestionDifficulty.EASY
        }
    ],
    QuestionCategory.LEADERSHIP: [
        {
            "template": "Tell me about a time you mentored someone or led a team initiative.",
            "purpose": "Assess leadership potential",
            "follow_ups": [
                "What was challenging about it?",
                "What would you do differently?"
            ],
            "difficulty": QuestionDifficulty.MEDIUM
        },
        {
            "template": "How do you handle disagreements within your team?",
            "purpose": "Evaluate conflict management",
            "follow_ups": ["Can you give a specific example?"],
            "difficulty": QuestionDifficulty.MEDIUM
        }
    ]
}


class InterviewQuestionsService:
    """Service for generating tailored interview questions."""
    
    def __init__(self):
        self._templates = QUESTION_TEMPLATES
        self._question_counter = 0
    
    def generate_interview_guide(
        self,
        candidate_data: Dict[str, Any],
        job_requirements: Optional[Dict[str, Any]] = None,
        num_questions: int = 10,
        categories: Optional[List[str]] = None,
        difficulty_mix: Optional[Dict[str, float]] = None
    ) -> InterviewGuide:
        """Generate a complete interview guide for a candidate.
        
        Args:
            candidate_data: Candidate information from CV
            job_requirements: Job requirements (skills, experience, etc.)
            num_questions: Number of questions to generate
            categories: Specific categories to include
            difficulty_mix: Distribution of difficulties (e.g., {"easy": 0.2, "medium": 0.5, "hard": 0.3})
            
        Returns:
            InterviewGuide with tailored questions
        """
        candidate_id = candidate_data.get("cv_id", candidate_data.get("id", "unknown"))
        candidate_name = candidate_data.get("name", candidate_data.get("candidate_name", "Unknown"))
        
        # Analyze candidate profile
        skills = self._extract_skills(candidate_data)
        experience = self._extract_experience(candidate_data)
        gaps = self._identify_gaps(candidate_data, job_requirements)
        strengths = self._identify_strengths(candidate_data, job_requirements)
        
        # Determine categories to cover
        if categories:
            [QuestionCategory(c) for c in categories]
        else:
            self._select_categories(candidate_data, job_requirements, gaps)
        
        # Set difficulty distribution
        if not difficulty_mix:
            difficulty_mix = {"easy": 0.2, "medium": 0.5, "hard": 0.3}
        
        # Generate questions
        questions = []
        
        # Technical questions for key skills
        tech_questions = self._generate_technical_questions(skills, job_requirements, 3)
        questions.extend(tech_questions)
        
        # Experience verification
        if experience:
            exp_questions = self._generate_experience_questions(experience, 2)
            questions.extend(exp_questions)
        
        # Gap exploration
        if gaps:
            gap_questions = self._generate_gap_questions(gaps, 2)
            questions.extend(gap_questions)
        
        # Behavioral questions
        behavioral_questions = self._generate_behavioral_questions(skills, 2)
        questions.extend(behavioral_questions)
        
        # Motivation question
        questions.append(self._generate_motivation_question())
        
        # Trim or pad to requested number
        questions = questions[:num_questions]
        
        # Calculate total time
        total_time = sum(q.time_estimate_minutes for q in questions)
        
        return InterviewGuide(
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            questions=questions,
            total_time_minutes=total_time,
            focus_areas=list({q.related_skill for q in questions if q.related_skill}),
            areas_to_probe=gaps[:3],
            strengths_to_confirm=strengths[:3]
        )
    
    def _extract_skills(self, candidate: Dict[str, Any]) -> List[str]:
        """Extract skills from candidate data."""
        skills = candidate.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",")]
        return skills[:10]  # Top 10 skills
    
    def _extract_experience(self, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract experience entries."""
        experiences = []
        
        # Try to get structured experience
        exp_list = candidate.get("experience", candidate.get("work_history", []))
        if isinstance(exp_list, list):
            experiences = exp_list[:3]
        
        # Fallback to current role
        current_role = candidate.get("current_role")
        if current_role and not experiences:
            experiences = [{"role": current_role}]
        
        return experiences
    
    def _identify_gaps(
        self,
        candidate: Dict[str, Any],
        requirements: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify skill/experience gaps."""
        gaps = []
        
        if not requirements:
            return gaps
        
        candidate_skills = {s.lower() for s in self._extract_skills(candidate)}
        required_skills = requirements.get("required_skills", [])
        
        for skill in required_skills:
            skill_lower = skill.lower()
            if not any(skill_lower in cs or cs in skill_lower for cs in candidate_skills):
                gaps.append(skill)
        
        # Check experience gap
        required_years = requirements.get("min_experience_years", 0)
        candidate_years = candidate.get("experience_years", 0) or 0
        if candidate_years < required_years:
            gaps.append(f"Experience ({candidate_years} vs {required_years} years required)")
        
        return gaps
    
    def _identify_strengths(
        self,
        candidate: Dict[str, Any],
        requirements: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify candidate strengths."""
        strengths = []
        
        candidate_skills = self._extract_skills(candidate)
        
        if requirements:
            required_skills = requirements.get("required_skills", [])
            for skill in required_skills:
                skill_lower = skill.lower()
                if any(skill_lower in cs.lower() for cs in candidate_skills):
                    strengths.append(f"Has {skill}")
        else:
            strengths = candidate_skills[:3]
        
        # Check experience strength
        years = candidate.get("experience_years", 0) or 0
        if years >= 5:
            strengths.append(f"{years}+ years experience")
        
        return strengths
    
    def _select_categories(
        self,
        candidate: Dict[str, Any],
        requirements: Optional[Dict[str, Any]],
        gaps: List[str]
    ) -> List[QuestionCategory]:
        """Select relevant question categories."""
        categories = [
            QuestionCategory.TECHNICAL,
            QuestionCategory.BEHAVIORAL,
            QuestionCategory.MOTIVATION
        ]
        
        if gaps:
            categories.append(QuestionCategory.GAP_EXPLORATION)
        
        # Add experience verification if detailed experience claimed
        if candidate.get("experience_years", 0) and candidate.get("experience_years", 0) > 3:
            categories.append(QuestionCategory.EXPERIENCE_VERIFICATION)
        
        return categories
    
    def _generate_technical_questions(
        self,
        skills: List[str],
        requirements: Optional[Dict[str, Any]],
        count: int
    ) -> List[InterviewQuestion]:
        """Generate technical questions for skills."""
        questions = []
        templates = self._templates.get(QuestionCategory.TECHNICAL, [])
        
        # Prioritize required skills
        priority_skills = []
        if requirements:
            priority_skills = requirements.get("required_skills", [])
        
        target_skills = priority_skills[:count] if priority_skills else skills[:count]
        
        for i, skill in enumerate(target_skills):
            if i >= len(templates):
                template = templates[0]
            else:
                template = templates[i % len(templates)]
            
            self._question_counter += 1
            question = InterviewQuestion(
                id=f"q_{self._question_counter}",
                question=template["template"].format(skill=skill),
                category=QuestionCategory.TECHNICAL,
                difficulty=template.get("difficulty", QuestionDifficulty.MEDIUM),
                purpose=template["purpose"].format(skill=skill),
                follow_ups=template.get("follow_ups", []),
                expected_signals=[f"Demonstrates practical knowledge of {skill}", "Clear explanation", "Real examples"],
                red_flags=["Vague answers", "Cannot provide examples", "Contradictions"],
                related_skill=skill,
                time_estimate_minutes=4
            )
            questions.append(question)
        
        return questions
    
    def _generate_experience_questions(
        self,
        experiences: List[Dict[str, Any]],
        count: int
    ) -> List[InterviewQuestion]:
        """Generate experience verification questions."""
        questions = []
        templates = self._templates.get(QuestionCategory.EXPERIENCE_VERIFICATION, [])
        
        for i, exp in enumerate(experiences[:count]):
            template = templates[i % len(templates)]
            
            exp_desc = exp.get("role", exp.get("title", "your previous role"))
            company = exp.get("company", "your previous company")
            
            self._question_counter += 1
            question = InterviewQuestion(
                id=f"q_{self._question_counter}",
                question=template["template"].format(experience=exp_desc, company=company),
                category=QuestionCategory.EXPERIENCE_VERIFICATION,
                difficulty=template.get("difficulty", QuestionDifficulty.EASY),
                purpose=template["purpose"].format(experience=exp_desc, company=company),
                follow_ups=template.get("follow_ups", []),
                expected_signals=["Specific details", "Clear metrics", "Consistent timeline"],
                red_flags=["Vague on details", "Inconsistent dates", "Cannot name colleagues"],
                time_estimate_minutes=3
            )
            questions.append(question)
        
        return questions
    
    def _generate_gap_questions(self, gaps: List[str], count: int) -> List[InterviewQuestion]:
        """Generate questions about identified gaps."""
        questions = []
        templates = self._templates.get(QuestionCategory.GAP_EXPLORATION, [])
        
        for i, gap in enumerate(gaps[:count]):
            template = templates[i % len(templates)]
            
            self._question_counter += 1
            question = InterviewQuestion(
                id=f"q_{self._question_counter}",
                question=template["template"].format(skill=gap, area=gap, target_area="this role"),
                category=QuestionCategory.GAP_EXPLORATION,
                difficulty=template.get("difficulty", QuestionDifficulty.MEDIUM),
                purpose=template["purpose"].format(skill=gap),
                follow_ups=template.get("follow_ups", []),
                expected_signals=["Awareness of gap", "Concrete learning plan", "Related experience"],
                red_flags=["Defensive response", "No plan to address", "Overconfidence"],
                related_skill=gap,
                time_estimate_minutes=3
            )
            questions.append(question)
        
        return questions
    
    def _generate_behavioral_questions(
        self,
        skills: List[str],
        count: int
    ) -> List[InterviewQuestion]:
        """Generate behavioral questions."""
        questions = []
        templates = self._templates.get(QuestionCategory.BEHAVIORAL, [])
        
        for i in range(count):
            template = templates[i % len(templates)]
            skill = skills[i % len(skills)] if skills else "new technology"
            
            self._question_counter += 1
            question = InterviewQuestion(
                id=f"q_{self._question_counter}",
                question=template["template"].format(skill=skill),
                category=QuestionCategory.BEHAVIORAL,
                difficulty=template.get("difficulty", QuestionDifficulty.MEDIUM),
                purpose=template["purpose"],
                follow_ups=template.get("follow_ups", []),
                expected_signals=["STAR format", "Self-awareness", "Growth mindset"],
                red_flags=["Blames others", "No self-reflection", "Hypothetical answers"],
                time_estimate_minutes=4
            )
            questions.append(question)
        
        return questions
    
    def _generate_motivation_question(self) -> InterviewQuestion:
        """Generate a motivation question."""
        templates = self._templates.get(QuestionCategory.MOTIVATION, [])
        template = templates[0]
        
        self._question_counter += 1
        return InterviewQuestion(
            id=f"q_{self._question_counter}",
            question=template["template"],
            category=QuestionCategory.MOTIVATION,
            difficulty=QuestionDifficulty.EASY,
            purpose=template["purpose"],
            follow_ups=template.get("follow_ups", []),
            expected_signals=["Research done", "Genuine interest", "Career alignment"],
            red_flags=["Generic answer", "Only mentions salary", "No research"],
            time_estimate_minutes=2
        )
    
    def generate_single_question(
        self,
        category: str,
        context: Optional[Dict[str, Any]] = None
    ) -> InterviewQuestion:
        """Generate a single question of a specific category."""
        cat = QuestionCategory(category)
        templates = self._templates.get(cat, [])
        
        if not templates:
            templates = self._templates[QuestionCategory.BEHAVIORAL]
        
        template = templates[0]
        skill = context.get("skill", "the topic") if context else "the topic"
        
        self._question_counter += 1
        return InterviewQuestion(
            id=f"q_{self._question_counter}",
            question=template["template"].format(
                skill=skill,
                experience=context.get("experience", "your experience") if context else "your experience",
                company=context.get("company", "your company") if context else "your company",
                area=context.get("area", "your area") if context else "your area",
                target_area=context.get("target_area", "this role") if context else "this role",
                scenario=context.get("scenario", "a real-world scenario") if context else "a real-world scenario"
            ),
            category=cat,
            difficulty=template.get("difficulty", QuestionDifficulty.MEDIUM),
            purpose=template["purpose"].format(skill=skill) if "{skill}" in template["purpose"] else template["purpose"],
            follow_ups=template.get("follow_ups", []),
            expected_signals=["Clear answer", "Specific examples"],
            red_flags=["Vague response"],
            related_skill=skill if skill != "the topic" else None,
            time_estimate_minutes=3
        )


# Singleton instance
_interview_service: Optional[InterviewQuestionsService] = None


def get_interview_service() -> InterviewQuestionsService:
    """Get singleton interview questions service instance."""
    global _interview_service
    if _interview_service is None:
        _interview_service = InterviewQuestionsService()
    return _interview_service
