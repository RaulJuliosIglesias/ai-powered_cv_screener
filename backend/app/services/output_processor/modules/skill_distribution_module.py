"""
SKILL DISTRIBUTION MODULE

Analyzes skill distribution across talent pool.
Used by: SummaryStructure
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)

# Valid technical skills - filter out garbage text
VALID_SKILLS = {
    # Programming Languages
    'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby', 'go', 'rust', 'php', 'swift', 'kotlin', 'scala', 'r',
    # Frontend
    'react', 'vue', 'angular', 'svelte', 'html', 'css', 'sass', 'tailwind', 'bootstrap', 'jquery',
    # Backend
    'node', 'nodejs', 'express', 'django', 'flask', 'fastapi', 'spring', 'rails', 'laravel', '.net', 'asp.net',
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb', 'oracle', 'sqlite',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ci/cd', 'linux', 'git',
    # Data & ML
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'spark', 'hadoop', 'data science',
    # Design & Creative
    '3d', 'maya', 'blender', 'zbrush', 'substance', 'photoshop', 'illustrator', 'figma', 'sketch', 'unity', 'unreal',
    # Soft Skills
    'leadership', 'management', 'communication', 'teamwork', 'agile', 'scrum', 'project management',
    # Other Technical
    'api', 'rest', 'graphql', 'microservices', 'blockchain', 'solidity', 'web3', 'security', 'networking',
    # Languages
    'english', 'spanish', 'french', 'german', 'chinese', 'japanese', 'portuguese',
    # VFX & Animation
    'vfx', 'animation', 'compositing', 'lighting', 'rigging', 'texturing', 'rendering', 'nuke', 'houdini', 'after effects',
    # Finance & Business
    'excel', 'financial analysis', 'accounting', 'budgeting', 'forecasting', 'sales', 'marketing',
    # Education
    'teaching', 'curriculum', 'training', 'mentoring', 'coaching',
}


@dataclass
class SkillStats:
    """Statistics for a single skill."""
    skill: str
    candidate_count: int
    percentage: float


@dataclass
class SkillDistributionData:
    """Container for skill distribution."""
    skills: List[SkillStats] = field(default_factory=list)
    total_candidates: int = 0
    top_skills: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "skills": [
                {"skill": s.skill, "candidate_count": s.candidate_count, "percentage": s.percentage}
                for s in self.skills
            ],
            "total_candidates": self.total_candidates,
            "top_skills": self.top_skills
        }


class SkillDistributionModule:
    """Module for analyzing skill distribution."""
    
    def analyze(self, chunks: List[Dict[str, Any]]) -> Optional[SkillDistributionData]:
        """Analyze skill distribution from chunks."""
        if not chunks:
            return None
        
        # Group by candidate and collect skills
        candidates = {}
        all_skills = Counter()
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            
            if not cv_id:
                continue
            
            if cv_id not in candidates:
                candidates[cv_id] = set()
            
            skills_str = meta.get("skills", "")
            if skills_str:
                for skill in skills_str.split(","):
                    skill = skill.strip().lower()
                    # Filter: must be valid skill, not too long, not garbage
                    if self._is_valid_skill(skill):
                        candidates[cv_id].add(skill)
        
        # Count skill occurrences
        for candidate_skills in candidates.values():
            for skill in candidate_skills:
                all_skills[skill] += 1
        
        total = len(candidates)
        
        # Build skill stats
        skill_stats = []
        for skill, count in all_skills.most_common(20):
            pct = (count / total * 100) if total > 0 else 0
            skill_stats.append(SkillStats(
                skill=skill.title(),
                candidate_count=count,
                percentage=round(pct, 1)
            ))
        
        top_skills = [s.skill for s in skill_stats[:5]]
        
        logger.info(f"[SKILL_DISTRIBUTION_MODULE] Found {len(all_skills)} unique skills")
        
        return SkillDistributionData(
            skills=skill_stats,
            total_candidates=total,
            top_skills=top_skills
        )
    
    def _is_valid_skill(self, skill: str) -> bool:
        """
        Check if a skill is valid and not garbage text.
        
        PHASE 7.2 FIX: Ultra-aggressive filtering to reject:
        - Sentence fragments (ending in period, starting with articles)
        - Person names (First Last pattern)
        - Location names
        - Generic/filler words
        """
        if not skill or len(skill) < 2:
            return False
        
        skill_lower = skill.lower().strip()
        skill_stripped = skill.strip()
        
        # PHASE 7.2: Reject strings ending with period (sentence fragments)
        if skill_stripped.endswith('.'):
            logger.debug(f"[SKILL_FILTER] Rejected (ends with period): {skill}")
            return False
        
        # PHASE 7.2: Reject if starts with article or preposition (sentence fragment)
        sentence_starters = ['the ', 'a ', 'an ', 'and ', 'or ', 'but ', 'while ', 
                            'new ', 'existing ', 'chain ', 'cross ', 'into ']
        if any(skill_lower.startswith(s) for s in sentence_starters):
            logger.debug(f"[SKILL_FILTER] Rejected (sentence starter): {skill}")
            return False
        
        # Too long - probably garbage
        if len(skill) > 30:
            return False
        
        # Contains URLs or emails
        if any(x in skill_lower for x in ['http', 'www', '.com', '.org', '@', '/']):
            return False
        
        # Contains numbers that look like stats
        if any(x in skill_lower for x in ['%', '+', '500', '100', 'award', 'received']):
            return False
        
        # Too many words - probably a sentence
        if len(skill.split()) > 3:
            logger.debug(f"[SKILL_FILTER] Rejected (too many words): {skill}")
            return False
        
        # PHASE 7.2: Reject sentence fragments with common verbs/gerunds
        fragment_words = {'implementing', 'ensuring', 'maintaining', 'designing', 
                         'enabling', 'delivering', 'managing', 'developing',
                         'creating', 'building', 'secure', 'security', 'protocol',
                         'communication', 'networks', 'procedures', 'existing'}
        words_set = set(skill_lower.split())
        if words_set & fragment_words and skill_lower not in VALID_SKILLS:
            logger.debug(f"[SKILL_FILTER] Rejected (fragment word): {skill}")
            return False
        
        # PHASE 7.2: Reject person names (two words, both capitalized properly)
        words = skill_stripped.split()
        if len(words) == 2:
            # Check if looks like "First Last" name pattern
            if (len(words[0]) >= 2 and len(words[1]) >= 2 and
                words[0][0].isupper() and words[1][0].isupper() and
                words[0][1:].islower() and words[1][1:].islower()):
                # It's a person name unless it's in VALID_SKILLS
                if skill_lower not in VALID_SKILLS:
                    logger.debug(f"[SKILL_FILTER] Rejected (person name): {skill}")
                    return False
        
        # Reject location names
        location_names = {
            'sydney', 'melbourne', 'brisbane', 'perth', 'berlin', 'munich',
            'london', 'paris', 'tokyo', 'singapore', 'dubai', 'mumbai',
            'new york', 'los angeles', 'chicago', 'san francisco', 'seattle',
            'toronto', 'vancouver', 'amsterdam', 'madrid', 'barcelona', 'rome', 'milan',
            'italy', 'germany', 'france', 'spain', 'australia', 'canada', 'usa', 'uk'
        }
        if skill_lower in location_names:
            return False
        
        # Reject generic/filler words
        garbage_words = {
            'based', 'technology', 'and', 'the', 'for', 'with', 'from', 'into',
            'profile', 'incidents', 'counseling', 'reliability', 'oriented', 'patient',
            'innovation', 'labs', 'solutions', 'services', 'consulting',
            'senior', 'junior', 'lead', 'manager', 'director', 'associate',
            'summary', 'objective', 'career', 'background', 'overview',
            'contact', 'email', 'phone', 'address', 'linkedin', 'github'
        }
        if skill_lower in garbage_words:
            return False
        
        # MUST match against valid skills list - no fuzzy acceptance
        for valid in VALID_SKILLS:
            if valid == skill_lower or skill_lower == valid:
                return True
            # Allow partial match only if skill is a known prefix/suffix
            if len(skill_lower) >= 3 and (valid.startswith(skill_lower) or skill_lower.startswith(valid)):
                return True
        
        logger.debug(f"[SKILL_FILTER] Rejected (not in valid list): {skill}")
        return False
    
    def format(self, data: SkillDistributionData) -> str:
        """Format skill distribution into markdown."""
        if not data or not data.skills:
            return ""
        
        lines = [
            "### 🛠️ Skill Distribution",
            "",
            f"**Top Skills in Pool:**",
            "",
            "| Skill | Candidates | % of Pool |",
            "|:------|:----------:|:---------:|",
        ]
        
        for s in data.skills[:10]:
            bar = "█" * int(s.percentage / 10)
            lines.append(f"| {s.skill} | {s.candidate_count} | {s.percentage:.0f}% {bar} |")
        
        return "\n".join(lines)
