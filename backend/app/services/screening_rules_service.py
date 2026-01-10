"""
Screening Rules Service - Automatic candidate filtering based on configurable rules.

V8 Feature: Define rules to automatically screen candidates based on requirements.
Rules can filter by skills, experience, education, location, etc.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RuleOperator(Enum):
    """Operators for rule conditions."""
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class RuleField(Enum):
    """Fields that can be used in rules."""
    SKILLS = "skills"
    EXPERIENCE_YEARS = "experience_years"
    EDUCATION = "education"
    EDUCATION_LEVEL = "education_level"
    CURRENT_ROLE = "current_role"
    LOCATION = "location"
    LANGUAGES = "languages"
    CERTIFICATIONS = "certifications"
    FULL_TEXT = "full_text"
    FILENAME = "filename"


class RuleAction(Enum):
    """Actions to take when rule matches."""
    INCLUDE = "include"  # Include candidate if rule matches
    EXCLUDE = "exclude"  # Exclude candidate if rule matches
    FLAG = "flag"        # Flag for review
    BOOST = "boost"      # Boost score
    PENALIZE = "penalize"  # Reduce score


@dataclass
class ScreeningRule:
    """A single screening rule."""
    id: str
    name: str
    field: RuleField
    operator: RuleOperator
    value: Any
    action: RuleAction
    priority: int = 0
    enabled: bool = True
    score_modifier: float = 0.0  # For BOOST/PENALIZE actions
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "field": self.field.value,
            "operator": self.operator.value,
            "value": self.value,
            "action": self.action.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "score_modifier": self.score_modifier,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreeningRule":
        return cls(
            id=data["id"],
            name=data["name"],
            field=RuleField(data["field"]),
            operator=RuleOperator(data["operator"]),
            value=data["value"],
            action=RuleAction(data["action"]),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            score_modifier=data.get("score_modifier", 0.0),
            description=data.get("description")
        )


@dataclass
class RuleResult:
    """Result of evaluating a rule against a candidate."""
    rule: ScreeningRule
    matched: bool
    field_value: Any = None
    message: Optional[str] = None


@dataclass
class ScreeningResult:
    """Complete screening result for a candidate."""
    candidate_id: str
    candidate_name: str
    passed: bool
    score_modifier: float = 0.0
    matched_rules: List[RuleResult] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    exclusion_reason: Optional[str] = None


@dataclass
class RuleSet:
    """A collection of rules for a screening session."""
    id: str
    name: str
    rules: List[ScreeningRule] = field(default_factory=list)
    require_all: bool = False  # True = AND logic, False = OR logic for INCLUDE rules
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "rules": [r.to_dict() for r in self.rules],
            "require_all": self.require_all
        }


class ScreeningRulesService:
    """Service for managing and evaluating screening rules."""
    
    def __init__(self):
        self._rule_sets: Dict[str, RuleSet] = {}
        self._session_rules: Dict[str, str] = {}  # session_id -> rule_set_id
    
    def create_rule_set(
        self,
        name: str,
        rules: List[Dict[str, Any]] = None,
        require_all: bool = False
    ) -> RuleSet:
        """Create a new rule set."""
        import uuid
        rule_set_id = str(uuid.uuid4())[:8]
        
        parsed_rules = []
        if rules:
            for i, rule_data in enumerate(rules):
                rule_data["id"] = rule_data.get("id", f"rule_{i}")
                parsed_rules.append(ScreeningRule.from_dict(rule_data))
        
        rule_set = RuleSet(
            id=rule_set_id,
            name=name,
            rules=parsed_rules,
            require_all=require_all
        )
        
        self._rule_sets[rule_set_id] = rule_set
        logger.info(f"[SCREENING] Created rule set '{name}' with {len(parsed_rules)} rules")
        
        return rule_set
    
    def add_rule(self, rule_set_id: str, rule: Dict[str, Any]) -> Optional[ScreeningRule]:
        """Add a rule to an existing rule set."""
        rule_set = self._rule_sets.get(rule_set_id)
        if not rule_set:
            return None
        
        rule["id"] = rule.get("id", f"rule_{len(rule_set.rules)}")
        parsed_rule = ScreeningRule.from_dict(rule)
        rule_set.rules.append(parsed_rule)
        
        logger.info(f"[SCREENING] Added rule '{parsed_rule.name}' to set {rule_set_id}")
        return parsed_rule
    
    def assign_to_session(self, session_id: str, rule_set_id: str) -> bool:
        """Assign a rule set to a session."""
        if rule_set_id not in self._rule_sets:
            return False
        self._session_rules[session_id] = rule_set_id
        return True
    
    def evaluate_candidate(
        self,
        candidate_data: Dict[str, Any],
        rule_set_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ScreeningResult:
        """Evaluate a candidate against rules.
        
        Args:
            candidate_data: Candidate information dict
            rule_set_id: Rule set to use (or use session's assigned set)
            session_id: Session ID to get assigned rules
            
        Returns:
            ScreeningResult with pass/fail and details
        """
        # Get rule set
        if rule_set_id:
            rule_set = self._rule_sets.get(rule_set_id)
        elif session_id:
            assigned_id = self._session_rules.get(session_id)
            rule_set = self._rule_sets.get(assigned_id) if assigned_id else None
        else:
            rule_set = None
        
        candidate_id = candidate_data.get("cv_id", candidate_data.get("id", "unknown"))
        candidate_name = candidate_data.get("name", candidate_data.get("candidate_name", "Unknown"))
        
        # No rules = pass everyone
        if not rule_set or not rule_set.rules:
            return ScreeningResult(
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                passed=True
            )
        
        # Evaluate each rule
        results: List[RuleResult] = []
        for rule in rule_set.rules:
            if not rule.enabled:
                continue
            result = self._evaluate_rule(rule, candidate_data)
            results.append(result)
        
        # Determine pass/fail
        return self._compute_result(candidate_id, candidate_name, results, rule_set.require_all)
    
    def _evaluate_rule(self, rule: ScreeningRule, candidate: Dict[str, Any]) -> RuleResult:
        """Evaluate a single rule against candidate data."""
        # Extract field value
        field_value = self._extract_field_value(rule.field, candidate)
        
        # Check if field exists
        if rule.operator == RuleOperator.EXISTS:
            matched = field_value is not None and field_value != ""
            return RuleResult(rule=rule, matched=matched, field_value=field_value)
        
        if rule.operator == RuleOperator.NOT_EXISTS:
            matched = field_value is None or field_value == ""
            return RuleResult(rule=rule, matched=matched, field_value=field_value)
        
        # Handle None values
        if field_value is None:
            return RuleResult(rule=rule, matched=False, field_value=None)
        
        # Evaluate based on operator
        matched = self._apply_operator(rule.operator, field_value, rule.value)
        
        message = None
        if matched:
            message = f"{rule.field.value} {rule.operator.value} '{rule.value}'"
        
        return RuleResult(rule=rule, matched=matched, field_value=field_value, message=message)
    
    def _extract_field_value(self, field: RuleField, candidate: Dict[str, Any]) -> Any:
        """Extract field value from candidate data."""
        if field == RuleField.SKILLS:
            skills = candidate.get("skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",")]
            return skills
        
        elif field == RuleField.EXPERIENCE_YEARS:
            return candidate.get("experience_years", candidate.get("years_experience"))
        
        elif field == RuleField.EDUCATION:
            return candidate.get("education", candidate.get("education_summary", ""))
        
        elif field == RuleField.EDUCATION_LEVEL:
            return candidate.get("education_level", candidate.get("degree_level", ""))
        
        elif field == RuleField.CURRENT_ROLE:
            return candidate.get("current_role", candidate.get("title", ""))
        
        elif field == RuleField.LOCATION:
            return candidate.get("location", candidate.get("city", ""))
        
        elif field == RuleField.LANGUAGES:
            langs = candidate.get("languages", [])
            if isinstance(langs, str):
                langs = [l.strip() for l in langs.split(",")]
            return langs
        
        elif field == RuleField.CERTIFICATIONS:
            certs = candidate.get("certifications", [])
            if isinstance(certs, str):
                certs = [c.strip() for c in certs.split(",")]
            return certs
        
        elif field == RuleField.FULL_TEXT:
            return candidate.get("content", candidate.get("full_text", ""))
        
        elif field == RuleField.FILENAME:
            return candidate.get("filename", "")
        
        return None
    
    def _apply_operator(self, operator: RuleOperator, field_value: Any, rule_value: Any) -> bool:
        """Apply operator to compare field value with rule value."""
        # Handle list fields
        if isinstance(field_value, list):
            field_value_lower = [str(v).lower() for v in field_value]
            
            if operator == RuleOperator.CONTAINS:
                return any(str(rule_value).lower() in v for v in field_value_lower)
            elif operator == RuleOperator.NOT_CONTAINS:
                return not any(str(rule_value).lower() in v for v in field_value_lower)
            elif operator == RuleOperator.IN_LIST:
                rule_list = [str(v).lower() for v in rule_value] if isinstance(rule_value, list) else [str(rule_value).lower()]
                return any(v in field_value_lower for v in rule_list)
            elif operator == RuleOperator.NOT_IN_LIST:
                rule_list = [str(v).lower() for v in rule_value] if isinstance(rule_value, list) else [str(rule_value).lower()]
                return not any(v in field_value_lower for v in rule_list)
        
        # Handle string fields
        if isinstance(field_value, str):
            field_lower = field_value.lower()
            rule_lower = str(rule_value).lower()
            
            if operator == RuleOperator.CONTAINS:
                return rule_lower in field_lower
            elif operator == RuleOperator.NOT_CONTAINS:
                return rule_lower not in field_lower
            elif operator == RuleOperator.EQUALS:
                return field_lower == rule_lower
            elif operator == RuleOperator.NOT_EQUALS:
                return field_lower != rule_lower
            elif operator == RuleOperator.REGEX:
                try:
                    return bool(re.search(str(rule_value), field_value, re.IGNORECASE))
                except:
                    return False
        
        # Handle numeric fields
        if isinstance(field_value, (int, float)):
            try:
                rule_num = float(rule_value)
                if operator == RuleOperator.EQUALS:
                    return field_value == rule_num
                elif operator == RuleOperator.NOT_EQUALS:
                    return field_value != rule_num
                elif operator == RuleOperator.GREATER_THAN:
                    return field_value > rule_num
                elif operator == RuleOperator.LESS_THAN:
                    return field_value < rule_num
                elif operator == RuleOperator.GREATER_OR_EQUAL:
                    return field_value >= rule_num
                elif operator == RuleOperator.LESS_OR_EQUAL:
                    return field_value <= rule_num
            except:
                return False
        
        return False
    
    def _compute_result(
        self,
        candidate_id: str,
        candidate_name: str,
        results: List[RuleResult],
        require_all: bool
    ) -> ScreeningResult:
        """Compute final screening result from rule evaluations."""
        passed = True
        score_modifier = 0.0
        flags = []
        exclusion_reason = None
        
        # Sort by priority
        sorted_results = sorted(results, key=lambda r: r.rule.priority, reverse=True)
        
        include_matches = []
        exclude_matches = []
        
        for result in sorted_results:
            if not result.matched:
                continue
            
            rule = result.rule
            
            if rule.action == RuleAction.EXCLUDE:
                exclude_matches.append(result)
                passed = False
                exclusion_reason = f"Excluded by rule: {rule.name}"
                
            elif rule.action == RuleAction.INCLUDE:
                include_matches.append(result)
                
            elif rule.action == RuleAction.FLAG:
                flags.append(rule.name)
                
            elif rule.action == RuleAction.BOOST:
                score_modifier += rule.score_modifier
                
            elif rule.action == RuleAction.PENALIZE:
                score_modifier -= rule.score_modifier
        
        # Handle INCLUDE logic
        include_rules = [r for r in sorted_results if r.rule.action == RuleAction.INCLUDE]
        if include_rules:
            if require_all:
                # All INCLUDE rules must match
                if len(include_matches) < len(include_rules):
                    passed = False
                    exclusion_reason = "Did not match all required criteria"
            else:
                # At least one INCLUDE rule must match
                if not include_matches:
                    passed = False
                    exclusion_reason = "Did not match any required criteria"
        
        return ScreeningResult(
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            passed=passed,
            score_modifier=score_modifier,
            matched_rules=sorted_results,
            flags=flags,
            exclusion_reason=exclusion_reason
        )
    
    def get_rule_set(self, rule_set_id: str) -> Optional[RuleSet]:
        """Get a rule set by ID."""
        return self._rule_sets.get(rule_set_id)
    
    def list_rule_sets(self) -> List[Dict[str, Any]]:
        """List all rule sets."""
        return [rs.to_dict() for rs in self._rule_sets.values()]
    
    def delete_rule_set(self, rule_set_id: str) -> bool:
        """Delete a rule set."""
        if rule_set_id in self._rule_sets:
            del self._rule_sets[rule_set_id]
            return True
        return False


# Singleton instance
_screening_service: Optional[ScreeningRulesService] = None


def get_screening_service() -> ScreeningRulesService:
    """Get singleton screening rules service instance."""
    global _screening_service
    if _screening_service is None:
        _screening_service = ScreeningRulesService()
    return _screening_service


# Preset rule templates
RULE_TEMPLATES = {
    "tech_senior": {
        "name": "Senior Tech Position",
        "rules": [
            {
                "name": "Min 5 years experience",
                "field": "experience_years",
                "operator": "greater_or_equal",
                "value": 5,
                "action": "include"
            },
            {
                "name": "Required programming skills",
                "field": "skills",
                "operator": "in_list",
                "value": ["python", "javascript", "java", "typescript"],
                "action": "include"
            }
        ],
        "require_all": True
    },
    "entry_level": {
        "name": "Entry Level Position",
        "rules": [
            {
                "name": "Max 2 years experience",
                "field": "experience_years",
                "operator": "less_or_equal",
                "value": 2,
                "action": "include"
            },
            {
                "name": "Has degree",
                "field": "education",
                "operator": "exists",
                "value": None,
                "action": "boost",
                "score_modifier": 0.1
            }
        ],
        "require_all": False
    }
}
