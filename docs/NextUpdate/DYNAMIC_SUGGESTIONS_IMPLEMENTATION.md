# Implementation Plan: Dynamic Contextual Suggestions System

## Document Purpose

Complete plan to implement a dynamic suggestions system that adapts to conversational context and previous query type. This plan **REUSES** the existing context infrastructure documented in `CONVERSATIONAL_CONTEXT_INTEGRATION_PLAN.md`.

**Reference Documents:**
- `docs/NextUpdate/CONVERSATIONAL_CONTEXT_INTEGRATION_PLAN.md` - Context infrastructure (REUSE)
- `docs/NextUpdate/ORCHESTRATION_STRUCTURES_MODULES.md` - 9 Implemented structures
- `docs/NextUpdate/IMPLEMENTATION_PLAN.md` - General plan

**Version:** 1.0  
**Date:** January 2026  
**Total Estimated Time:** 12-15 hours

---

# PART 1: CURRENT STATE ANALYSIS

## 1.1 Current Suggestions System (TO REPLACE)

### ❌ **Current Implementation - BASIC**

**File:** `backend/app/api/routes_sessions.py:629-695`

```python
@router.get("/{session_id}/suggestions")
async def get_suggested_questions(session_id: str, mode: Mode):
    # Only 10 hardcoded generic questions
    generic_questions = [
        f"Rank all {num_cvs} candidates by experience",
        "Who is best for a leadership role?",
        "Who has the strongest technical skills?",
        # ... 7 more
    ]
    random.shuffle(generic_questions)
    suggestions = generic_questions[:4]  # Random 4
```

**Problems:**
- ❌ Only 10 static questions
- ❌ Does not consider conversation context
- ❌ Does not consider previous query_type
- ❌ Does not personalize with mentioned candidate names
- ❌ Always the same questions with random rotation

---

## 1.2 EXISTING Context Infrastructure (REUSE)

### ✅ **get_conversation_history() - IMPLEMENTED**

```python
# SessionManager Local - sessions.py:201-218
def get_conversation_history(session_id: str, limit: int = 6) -> List[ChatMessage]

# SessionManager Cloud - sessions.py:299-336  
def get_conversation_history(session_id: str, limit: int = 6) -> List[Dict]
```

**REUSE:** Already retrieves last N messages with format `[{"role": "user|assistant", "content": "..."}]`

### ✅ **ChatMessage with Metadata - IMPLEMENTED**

```python
# ChatMessage stores:
- role: str           # "user" | "assistant"
- content: str        # Complete message
- sources: List       # Sources used
- pipeline_steps: List  # Pipeline steps
- structured_output: Dict  # ← CONTAINS query_type!
```

**REUSE:** The `structured_output` already contains `structure_type` which tells us the query_type of each response.

### ✅ **9 Query Types in Orchestrator - IMPLEMENTED**

```python
# orchestrator.py - Supported query types:
"single_candidate" → SingleCandidateStructure
"red_flags"        → RiskAssessmentStructure
"comparison"       → ComparisonStructure
"search"           → SearchStructure
"ranking"          → RankingStructure
"job_match"        → JobMatchStructure
"team_build"       → TeamBuildStructure
"verification"     → VerificationStructure
"summary"          → SummaryStructure
```

**REUSE:** These 9 types determine which suggestion bank to use.

---

## 1.3 Query Type → Suggestions Transition Matrix

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRANSITION MATRIX                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   AFTER              →    PRIMARILY SUGGEST                         │
│   ─────────────────────────────────────────                         │
│   (no context)       →    search, summary, single_candidate         │
│   search             →    ranking, comparison, single_candidate     │
│   ranking            →    single_candidate, comparison, risk        │
│   comparison         →    single_candidate, risk, verification      │
│   job_match          →    comparison, risk, single_candidate        │
│   team_build         →    risk, skill_coverage, alternatives        │
│   single_candidate   →    risk, comparison, verification, job_match │
│   red_flags          →    comparison, single_candidate, mitigation  │
│   verification       →    single_candidate, risk, comparison        │
│   summary            →    search, ranking, single_candidate         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

# PART 2: SYSTEM ARCHITECTURE

## 2.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SUGGESTION ENGINE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐                                               │
│  │    ENDPOINT      │ GET /api/sessions/{id}/suggestions            │
│  │ routes_sessions  │                                               │
│  └────────┬─────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────┐    ┌───────────────────────────────────────┐  │
│  │  SessionManager  │───▶│ REUSAR: get_conversation_history()   │  │
│  │    (existente)   │    │         get_last_query_type()  [NEW]  │  │
│  └──────────────────┘    └───────────────────────────────────────┘  │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   SuggestionEngine                            │   │
│  │                                                               │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │   │
│  │  │   Context      │  │   Suggestion   │  │   Template     │  │   │
│  │  │   Extractor    │→ │   Selector     │→ │   Filler       │  │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘  │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   SUGGESTION BANKS                            │   │
│  │                                                               │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │   │
│  │  │ INITIAL │ │ SEARCH  │ │ RANKING │ │ COMPARE │ │JOB_MATCH│ │   │
│  │  │  (~15)  │ │  (~15)  │ │  (~15)  │ │  (~15)  │ │  (~12)  │ │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             │   │
│  │  │TEAM_BLD │ │SINGLE_C │ │RED_FLAGS│ │ VERIFY  │  TOTAL:    │   │
│  │  │  (~12)  │ │  (~15)  │ │  (~12)  │ │  (~10)  │  ~120      │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘             │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2.2 File Structure to Create

```
backend/app/services/suggestion_engine/
├── __init__.py                    # Exports SuggestionEngine
├── engine.py                      # Main SuggestionEngine class
├── context_extractor.py           # Extracts info from conversational context
├── suggestion_selector.py         # Selects appropriate suggestions
├── template_filler.py             # Fills placeholders in suggestions
└── banks/
    ├── __init__.py                # Exports all banks
    ├── base.py                    # Dataclass Suggestion, SuggestionBank
    ├── initial_bank.py            # Suggestions without prior context
    ├── search_bank.py             # Suggestions post-search
    ├── ranking_bank.py            # Suggestions post-ranking
    ├── comparison_bank.py         # Suggestions post-comparison
    ├── job_match_bank.py          # Suggestions post-job_match
    ├── team_build_bank.py         # Suggestions post-team_build
    ├── single_candidate_bank.py   # Suggestions post-single_candidate
    ├── risk_assessment_bank.py    # Suggestions post-red_flags
    └── verification_bank.py       # Suggestions post-verification
```

**Total:** 14 new files

---

# PART 3: PHASED IMPLEMENTATION PLAN

## **PHASE 1: Base Infrastructure (3-4 hours)**

### Objective
Create SuggestionEngine structure and base classes.

### Tasks

#### ✅ **Task 1.1: Create directory structure**

```bash
mkdir -p backend/app/services/suggestion_engine/banks
```

---

#### ✅ **Task 1.2: Create banks/base.py**

**File:** `backend/app/services/suggestion_engine/banks/base.py`

```python
"""
Base classes for suggestion banks.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class SuggestionCategory(str, Enum):
    """Maps to query_type from Orchestrator."""
    INITIAL = "initial"           # No previous context
    SEARCH = "search"
    RANKING = "ranking"
    COMPARISON = "comparison"
    JOB_MATCH = "job_match"
    TEAM_BUILD = "team_build"
    SINGLE_CANDIDATE = "single_candidate"
    RISK_ASSESSMENT = "risk_assessment"  # red_flags
    VERIFICATION = "verification"
    SUMMARY = "summary"


@dataclass
class Suggestion:
    """
    A single suggestion template.
    
    Placeholders:
    - {candidate_name} - Will be filled with mentioned candidate
    - {skill} - Will be filled with mentioned skill
    - {role} - Will be filled with mentioned role
    - {num_cvs} - Will be filled with CV count
    """
    text: str
    category: SuggestionCategory
    
    # Placeholder requirements
    requires_candidate: bool = False   # Needs {candidate_name}
    requires_skill: bool = False       # Needs {skill}
    requires_role: bool = False        # Needs {role}
    requires_multiple_cvs: bool = False  # Needs >1 CVs
    
    # Filtering
    min_cvs: int = 1                   # Minimum CVs to show this
    priority: int = 1                  # 1=high, 2=medium, 3=low
    
    # Tracking
    id: str = ""                       # Auto-generated for dedup
    
    def __post_init__(self):
        # Auto-generate ID from text hash
        if not self.id:
            self.id = f"sug_{hash(self.text) % 100000:05d}"


@dataclass
class SuggestionBank:
    """
    A collection of suggestions for a specific category.
    """
    category: SuggestionCategory
    suggestions: List[Suggestion] = field(default_factory=list)
    
    def get_applicable(
        self,
        num_cvs: int,
        has_candidate: bool,
        has_skill: bool,
        has_role: bool
    ) -> List[Suggestion]:
        """
        Filter suggestions that can be filled with available context.
        """
        applicable = []
        for s in self.suggestions:
            # Check CV requirement
            if s.min_cvs > num_cvs:
                continue
            if s.requires_multiple_cvs and num_cvs < 2:
                continue
            
            # Check placeholder requirements
            if s.requires_candidate and not has_candidate:
                continue
            if s.requires_skill and not has_skill:
                continue
            if s.requires_role and not has_role:
                continue
            
            applicable.append(s)
        
        return applicable
```

**Estimación:** 30 minutos

---

#### ✅ **Tarea 1.3: Crear context_extractor.py**

**Archivo:** `backend/app/services/suggestion_engine/context_extractor.py`

```python
"""
Extracts contextual information from conversation history.

REUTILIZA la infraestructura existente de get_conversation_history().
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

from app.prompts.templates import TECHNICAL_SKILLS_TAXONOMY

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContext:
    """
    Context extracted from conversation history.
    
    This is what the SuggestionSelector uses to pick suggestions.
    """
    # Query type info
    last_query_type: str = "initial"      # From structured_output.structure_type
    query_types_in_session: Set[str] = field(default_factory=set)
    
    # Entities mentioned
    mentioned_candidates: List[str] = field(default_factory=list)
    mentioned_skills: List[str] = field(default_factory=list)
    mentioned_roles: List[str] = field(default_factory=list)
    
    # Session info
    num_cvs: int = 0
    cv_names: List[str] = field(default_factory=list)
    
    # Analysis
    num_messages: int = 0
    is_first_query: bool = True


class ContextExtractor:
    """
    Extracts context from conversation history and session data.
    
    REUTILIZA:
    - conversation_history from get_conversation_history()
    - structured_output from ChatMessage (contains structure_type)
    """
    
    # CV reference pattern: **[Name](cv:cv_xxx)**
    CV_REFERENCE_PATTERN = re.compile(
        r'\*\*\[([^\]]+)\]\(cv:cv_[a-f0-9]+\)\*\*',
        re.IGNORECASE
    )
    
    # Alternative pattern: [📄](cv:cv_xxx) **Name**
    CV_ICON_PATTERN = re.compile(
        r'\[📄\]\(cv:cv_[a-f0-9]+\)\s*\*\*([^*]+)\*\*',
        re.IGNORECASE
    )
    
    def __init__(self):
        # Build skill lookup from taxonomy
        self.all_skills: Set[str] = set()
        for category, skills in TECHNICAL_SKILLS_TAXONOMY.items():
            self.all_skills.update(s.lower() for s in skills)
        
        # Common role keywords
        self.role_keywords = {
            "backend", "frontend", "fullstack", "devops", "data",
            "senior", "junior", "lead", "manager", "architect",
            "engineer", "developer", "analyst", "designer"
        }
    
    def extract(
        self,
        messages: List[Dict],
        cv_names: List[str],
        num_cvs: int
    ) -> ExtractedContext:
        """
        Extract context from conversation history.
        
        Args:
            messages: From get_conversation_history() - list of dicts with role/content
            cv_names: Names of CVs in session
            num_cvs: Number of CVs in session
            
        Returns:
            ExtractedContext with all extracted information
        """
        context = ExtractedContext(
            num_cvs=num_cvs,
            cv_names=cv_names,
            num_messages=len(messages),
            is_first_query=len(messages) == 0
        )
        
        if not messages:
            return context
        
        # Process messages in reverse (most recent first)
        for i, msg in enumerate(reversed(messages)):
            content = msg.get("content", "")
            role = msg.get("role", "")
            structured_output = msg.get("structured_output", {})
            
            # Extract query_type from structured_output
            if structured_output:
                structure_type = structured_output.get("structure_type")
                if structure_type:
                    context.query_types_in_session.add(structure_type)
                    if i == 0 and role == "assistant":  # Most recent
                        context.last_query_type = structure_type
            
            # Extract candidates from assistant responses
            if role == "assistant":
                candidates = self._extract_candidates(content)
                for c in candidates:
                    if c not in context.mentioned_candidates:
                        context.mentioned_candidates.append(c)
            
            # Extract skills and roles from user queries
            if role == "user":
                skills = self._extract_skills(content)
                for s in skills:
                    if s not in context.mentioned_skills:
                        context.mentioned_skills.append(s)
                
                roles = self._extract_roles(content)
                for r in roles:
                    if r not in context.mentioned_roles:
                        context.mentioned_roles.append(r)
        
        # Limit lists to most recent
        context.mentioned_candidates = context.mentioned_candidates[:5]
        context.mentioned_skills = context.mentioned_skills[:5]
        context.mentioned_roles = context.mentioned_roles[:3]
        
        logger.info(
            f"[SUGGESTION_ENGINE] Extracted context: "
            f"last_type={context.last_query_type}, "
            f"candidates={len(context.mentioned_candidates)}, "
            f"skills={len(context.mentioned_skills)}"
        )
        
        return context
    
    def _extract_candidates(self, text: str) -> List[str]:
        """Extract candidate names from response text."""
        candidates = []
        
        # Pattern 1: **[Name](cv:cv_xxx)**
        for match in self.CV_REFERENCE_PATTERN.finditer(text):
            name = match.group(1).strip()
            if name and name not in candidates:
                candidates.append(name)
        
        # Pattern 2: [📄](cv:cv_xxx) **Name**
        for match in self.CV_ICON_PATTERN.finditer(text):
            name = match.group(1).strip()
            if name and name not in candidates:
                candidates.append(name)
        
        return candidates
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skill names from query text."""
        text_lower = text.lower()
        found = []
        
        for skill in self.all_skills:
            # Word boundary check
            pattern = rf'\b{re.escape(skill)}\b'
            if re.search(pattern, text_lower):
                found.append(skill)
        
        return found
    
    def _extract_roles(self, text: str) -> List[str]:
        """Extract role mentions from query text."""
        text_lower = text.lower()
        found = []
        
        # Common role patterns
        role_patterns = [
            r'\b(backend\s+developer)\b',
            r'\b(frontend\s+developer)\b',
            r'\b(fullstack\s+developer)\b',
            r'\b(senior\s+engineer)\b',
            r'\b(tech\s+lead)\b',
            r'\b(data\s+scientist)\b',
            r'\b(devops\s+engineer)\b',
            r'\b(software\s+architect)\b',
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, text_lower)
            if match:
                role = match.group(1).title()
                if role not in found:
                    found.append(role)
        
        return found
```

**Estimación:** 1 hora

---

#### ✅ **Tarea 1.4: Crear suggestion_selector.py**

**Archivo:** `backend/app/services/suggestion_engine/suggestion_selector.py`

```python
"""
Selects and prioritizes suggestions based on context.
"""
import random
import logging
from typing import List, Set, Dict

from .banks.base import Suggestion, SuggestionCategory
from .context_extractor import ExtractedContext

logger = logging.getLogger(__name__)


class SuggestionSelector:
    """
    Selects appropriate suggestions based on extracted context.
    
    Implements:
    - Query type → Bank mapping
    - Deduplication (tracks used suggestions per session)
    - Priority-based selection
    - Fallback to generic suggestions
    """
    
    # Map query_type to suggestion category
    QUERY_TYPE_MAP: Dict[str, SuggestionCategory] = {
        "single_candidate": SuggestionCategory.SINGLE_CANDIDATE,
        "red_flags": SuggestionCategory.RISK_ASSESSMENT,
        "risk_assessment": SuggestionCategory.RISK_ASSESSMENT,
        "comparison": SuggestionCategory.COMPARISON,
        "search": SuggestionCategory.SEARCH,
        "ranking": SuggestionCategory.RANKING,
        "job_match": SuggestionCategory.JOB_MATCH,
        "team_build": SuggestionCategory.TEAM_BUILD,
        "verification": SuggestionCategory.VERIFICATION,
        "summary": SuggestionCategory.SUMMARY,
        "initial": SuggestionCategory.INITIAL,
    }
    
    def __init__(self, banks: Dict[SuggestionCategory, List[Suggestion]]):
        """
        Args:
            banks: Dict mapping category to list of suggestions
        """
        self.banks = banks
        self._used_ids: Set[str] = set()  # Track used suggestion IDs
    
    def select(
        self,
        context: ExtractedContext,
        count: int = 4
    ) -> List[Suggestion]:
        """
        Select suggestions based on context.
        
        Algorithm:
        1. Determine target category from last_query_type
        2. Filter applicable suggestions (placeholders can be filled)
        3. Remove already used suggestions
        4. Sort by priority
        5. Select top N
        6. Fallback to INITIAL if not enough
        
        Args:
            context: Extracted context from conversation
            count: Number of suggestions to return
            
        Returns:
            List of selected Suggestion objects
        """
        # Determine category from last query type
        category = self.QUERY_TYPE_MAP.get(
            context.last_query_type,
            SuggestionCategory.INITIAL
        )
        
        # Get bank for this category
        bank = self.banks.get(category, [])
        
        # Check what placeholders we can fill
        has_candidate = len(context.mentioned_candidates) > 0
        has_skill = len(context.mentioned_skills) > 0
        has_role = len(context.mentioned_roles) > 0 or has_skill
        
        # Filter applicable suggestions
        applicable = []
        for s in bank:
            # Check min_cvs
            if s.min_cvs > context.num_cvs:
                continue
            if s.requires_multiple_cvs and context.num_cvs < 2:
                continue
            
            # Check placeholder requirements
            if s.requires_candidate and not has_candidate:
                continue
            if s.requires_skill and not has_skill:
                continue
            if s.requires_role and not has_role:
                continue
            
            # Check not already used
            if s.id in self._used_ids:
                continue
            
            applicable.append(s)
        
        # Sort by priority (lower = higher priority)
        applicable.sort(key=lambda x: x.priority)
        
        # Select with some randomization within priority groups
        selected = []
        by_priority: Dict[int, List[Suggestion]] = {}
        
        for s in applicable:
            if s.priority not in by_priority:
                by_priority[s.priority] = []
            by_priority[s.priority].append(s)
        
        for priority in sorted(by_priority.keys()):
            group = by_priority[priority]
            random.shuffle(group)
            for s in group:
                if len(selected) >= count:
                    break
                selected.append(s)
                self._used_ids.add(s.id)
            if len(selected) >= count:
                break
        
        # Fallback to INITIAL bank if not enough
        if len(selected) < count:
            initial_bank = self.banks.get(SuggestionCategory.INITIAL, [])
            for s in initial_bank:
                if s.id in self._used_ids:
                    continue
                if s.min_cvs > context.num_cvs:
                    continue
                if s.requires_candidate and not has_candidate:
                    continue
                
                selected.append(s)
                self._used_ids.add(s.id)
                if len(selected) >= count:
                    break
        
        logger.info(
            f"[SUGGESTION_SELECTOR] Selected {len(selected)} suggestions "
            f"from category={category.value}"
        )
        
        return selected
    
    def reset(self):
        """Reset used suggestions (call on new session)."""
        self._used_ids.clear()
```

**Estimación:** 45 minutos

---

#### ✅ **Tarea 1.5: Crear template_filler.py**

**Archivo:** `backend/app/services/suggestion_engine/template_filler.py`

```python
"""
Fills placeholders in suggestion templates with actual values.
"""
import random
import logging
from typing import List

from .banks.base import Suggestion
from .context_extractor import ExtractedContext

logger = logging.getLogger(__name__)


class TemplateFiller:
    """
    Fills placeholders in suggestions with context values.
    
    Placeholders:
    - {candidate_name} → Mentioned candidate name
    - {skill} → Mentioned skill
    - {role} → Mentioned or default role
    - {num_cvs} → Number of CVs
    """
    
    # Default roles to use when none mentioned
    DEFAULT_ROLES = [
        "Backend Developer",
        "Frontend Developer",
        "Senior Engineer",
        "Tech Lead",
        "Data Scientist"
    ]
    
    def fill(
        self,
        suggestions: List[Suggestion],
        context: ExtractedContext
    ) -> List[str]:
        """
        Fill placeholders in suggestions with context values.
        
        Args:
            suggestions: Selected suggestions to fill
            context: Extracted context with values
            
        Returns:
            List of filled suggestion strings
        """
        filled = []
        
        for suggestion in suggestions:
            text = suggestion.text
            
            # Fill {candidate_name}
            if "{candidate_name}" in text:
                if context.mentioned_candidates:
                    name = random.choice(context.mentioned_candidates)
                elif context.cv_names:
                    name = random.choice(context.cv_names)
                else:
                    # Skip this suggestion if no name available
                    continue
                text = text.replace("{candidate_name}", name)
            
            # Fill {skill}
            if "{skill}" in text:
                if context.mentioned_skills:
                    skill = random.choice(context.mentioned_skills)
                else:
                    # Skip this suggestion if no skill available
                    continue
                text = text.replace("{skill}", skill.title())
            
            # Fill {role}
            if "{role}" in text:
                if context.mentioned_roles:
                    role = random.choice(context.mentioned_roles)
                else:
                    role = random.choice(self.DEFAULT_ROLES)
                text = text.replace("{role}", role)
            
            # Fill {num_cvs}
            text = text.replace("{num_cvs}", str(context.num_cvs))
            
            filled.append(text)
        
        logger.info(f"[TEMPLATE_FILLER] Filled {len(filled)} suggestions")
        
        return filled
```

**Estimación:** 30 minutos

---

### **Entregables Fase 1**
- [ ] Estructura de directorios creada
- [ ] `banks/base.py` con Suggestion y SuggestionBank
- [ ] `context_extractor.py` funcionando
- [ ] `suggestion_selector.py` con lógica de selección
- [ ] `template_filler.py` con relleno de placeholders

---

## **FASE 2: Bancos de Sugerencias (~120 sugerencias) (4-5 horas)**

### Objetivo
Crear los 9 bancos de sugerencias con ~15 sugerencias cada uno.

### Tareas

#### ✅ **Tarea 2.1: Crear initial_bank.py**

**Archivo:** `backend/app/services/suggestion_engine/banks/initial_bank.py`

```python
"""
Suggestions for first query (no previous context).
"""
from .base import Suggestion, SuggestionCategory

INITIAL_SUGGESTIONS = [
    # Overview
    Suggestion(
        text="Resumen general del talent pool",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Qué tecnologías dominan los candidatos?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Cuántos candidatos tienen experiencia senior?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    
    # Single candidate
    Suggestion(
        text="Dame el perfil completo de {candidate_name}",
        category=SuggestionCategory.INITIAL,
        requires_candidate=True,
        priority=1
    ),
    
    # Ranking
    Suggestion(
        text="Ranking de candidatos por experiencia",
        category=SuggestionCategory.INITIAL,
        min_cvs=3,
        requires_multiple_cvs=True,
        priority=1
    ),
    Suggestion(
        text="¿Quién tiene más experiencia total?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    
    # Search
    Suggestion(
        text="¿Quién tiene experiencia con Python?",
        category=SuggestionCategory.INITIAL,
        min_cvs=1,
        priority=2
    ),
    Suggestion(
        text="¿Hay candidatos con experiencia en startups?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Buscar candidatos con experiencia en liderazgo",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    
    # Comparison
    Suggestion(
        text="Comparar los dos candidatos más experimentados",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        requires_multiple_cvs=True,
        priority=2
    ),
    
    # Risk
    Suggestion(
        text="¿Hay candidatos con red flags de estabilidad?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
    
    # Skills
    Suggestion(
        text="¿Cuáles son los skills más comunes?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="¿Quién tiene el perfil más diverso?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
    
    # Education
    Suggestion(
        text="¿Qué nivel educativo tienen los candidatos?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
]
```

---

#### ✅ **Tarea 2.2: Crear search_bank.py**

```python
"""
Suggestions after a SEARCH query.
"""
from .base import Suggestion, SuggestionCategory

SEARCH_SUGGESTIONS = [
    # Refine search
    Suggestion(
        text="¿Cuántos años de experiencia tienen con {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="¿Quién tiene nivel senior en {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Buscar candidatos con {skill} y experiencia en liderazgo",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    
    # Pivot to ranking
    Suggestion(
        text="Rankear los que tienen {skill} por experiencia total",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    
    # Pivot to comparison
    Suggestion(
        text="Comparar los dos mejores candidatos con {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    
    # Deep dive
    Suggestion(
        text="Dame el perfil completo de {candidate_name}",
        category=SuggestionCategory.SEARCH,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="¿Qué otras tecnologías domina {candidate_name}?",
        category=SuggestionCategory.SEARCH,
        requires_candidate=True,
        priority=2
    ),
    
    # Certifications
    Suggestion(
        text="¿Alguno tiene certificaciones en {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=2
    ),
    
    # Expand
    Suggestion(
        text="¿Qué otras tecnologías conocen estos candidatos?",
        category=SuggestionCategory.SEARCH,
        priority=2
    ),
    Suggestion(
        text="¿Quién tiene experiencia similar pero en otro stack?",
        category=SuggestionCategory.SEARCH,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Buscar candidatos con skills complementarios a {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=2
    ),
    
    # Alternatives
    Suggestion(
        text="¿Hay candidatos que podrían aprender {skill} rápido?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=3
    ),
    Suggestion(
        text="Candidatos con tecnologías alternativas a {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=3
    ),
]
```

---

#### ✅ **Tarea 2.3: Crear ranking_bank.py**

```python
"""
Suggestions after a RANKING query.
"""
from .base import Suggestion, SuggestionCategory

RANKING_SUGGESTIONS = [
    # Explore top picks
    Suggestion(
        text="¿Por qué {candidate_name} está en el top del ranking?",
        category=SuggestionCategory.RANKING,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Dame el perfil completo del candidato #1",
        category=SuggestionCategory.RANKING,
        priority=1
    ),
    Suggestion(
        text="Compara el #1 vs #2 del ranking",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=1
    ),
    
    # Refine ranking
    Suggestion(
        text="¿Cómo cambia el ranking si priorizamos {skill}?",
        category=SuggestionCategory.RANKING,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Ranking excluyendo candidatos sin experiencia senior",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=2
    ),
    
    # Risk assessment
    Suggestion(
        text="¿Hay red flags en el top 3?",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Análisis de riesgos del candidato #1",
        category=SuggestionCategory.RANKING,
        priority=1
    ),
    Suggestion(
        text="¿Qué gaps tienen los candidatos top?",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=2
    ),
    
    # Team building
    Suggestion(
        text="¿Puedo armar un equipo con el top 3?",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=2
    ),
    Suggestion(
        text="¿Son complementarios los top candidatos?",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=2
    ),
    
    # Job match
    Suggestion(
        text="Match del #1 con rol de {role}",
        category=SuggestionCategory.RANKING,
        requires_role=True,
        priority=2
    ),
    Suggestion(
        text="¿Quién del top 3 encaja mejor para {role}?",
        category=SuggestionCategory.RANKING,
        requires_role=True,
        min_cvs=3,
        priority=2
    ),
    
    # Deep dive
    Suggestion(
        text="¿Cuál es la trayectoria de carrera de {candidate_name}?",
        category=SuggestionCategory.RANKING,
        requires_candidate=True,
        priority=2
    ),
]
```

---

#### ✅ **Tarea 2.4 - 2.9: Crear bancos restantes**

Crear de forma similar:
- `comparison_bank.py` (~15 sugerencias)
- `job_match_bank.py` (~12 sugerencias)
- `team_build_bank.py` (~12 sugerencias)
- `single_candidate_bank.py` (~15 sugerencias)
- `risk_assessment_bank.py` (~12 sugerencias)
- `verification_bank.py` (~10 sugerencias)

**Estimación total Fase 2:** 4-5 horas

---

### **Entregables Fase 2**
- [ ] 9 bancos de sugerencias creados
- [ ] ~120 sugerencias totales
- [ ] Todas las sugerencias con placeholders correctos
- [ ] Prioridades asignadas

---

## **FASE 3: Integración con API (2-3 horas)**

### Objetivo
Integrar SuggestionEngine con el endpoint de sugerencias existente.

### Tareas

#### ✅ **Tarea 3.1: Crear engine.py**

**Archivo:** `backend/app/services/suggestion_engine/engine.py`

```python
"""
Main SuggestionEngine - Entry point for suggestion generation.
"""
import logging
from typing import List, Dict, Optional

from .context_extractor import ContextExtractor, ExtractedContext
from .suggestion_selector import SuggestionSelector
from .template_filler import TemplateFiller
from .banks.base import SuggestionCategory

# Import all banks
from .banks.initial_bank import INITIAL_SUGGESTIONS
from .banks.search_bank import SEARCH_SUGGESTIONS
from .banks.ranking_bank import RANKING_SUGGESTIONS
from .banks.comparison_bank import COMPARISON_SUGGESTIONS
from .banks.job_match_bank import JOB_MATCH_SUGGESTIONS
from .banks.team_build_bank import TEAM_BUILD_SUGGESTIONS
from .banks.single_candidate_bank import SINGLE_CANDIDATE_SUGGESTIONS
from .banks.risk_assessment_bank import RISK_ASSESSMENT_SUGGESTIONS
from .banks.verification_bank import VERIFICATION_SUGGESTIONS

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Main engine for generating contextual suggestions.
    
    REUTILIZA:
    - get_conversation_history() from SessionManager
    - structure_type from StructuredOutput
    
    Usage:
        engine = SuggestionEngine()
        suggestions = engine.get_suggestions(
            messages=mgr.get_conversation_history(session_id),
            cv_names=["Juan", "María"],
            num_cvs=2
        )
    """
    
    def __init__(self):
        self.extractor = ContextExtractor()
        self.filler = TemplateFiller()
        
        # Build banks map
        self.banks = {
            SuggestionCategory.INITIAL: INITIAL_SUGGESTIONS,
            SuggestionCategory.SEARCH: SEARCH_SUGGESTIONS,
            SuggestionCategory.RANKING: RANKING_SUGGESTIONS,
            SuggestionCategory.COMPARISON: COMPARISON_SUGGESTIONS,
            SuggestionCategory.JOB_MATCH: JOB_MATCH_SUGGESTIONS,
            SuggestionCategory.TEAM_BUILD: TEAM_BUILD_SUGGESTIONS,
            SuggestionCategory.SINGLE_CANDIDATE: SINGLE_CANDIDATE_SUGGESTIONS,
            SuggestionCategory.RISK_ASSESSMENT: RISK_ASSESSMENT_SUGGESTIONS,
            SuggestionCategory.VERIFICATION: VERIFICATION_SUGGESTIONS,
        }
        
        self.selector = SuggestionSelector(self.banks)
        
        logger.info(
            f"[SUGGESTION_ENGINE] Initialized with "
            f"{sum(len(b) for b in self.banks.values())} total suggestions"
        )
    
    def get_suggestions(
        self,
        messages: List[Dict],
        cv_names: List[str],
        num_cvs: int,
        count: int = 4
    ) -> List[str]:
        """
        Generate contextual suggestions.
        
        Args:
            messages: From get_conversation_history()
            cv_names: Names of CVs in session
            num_cvs: Number of CVs
            count: Number of suggestions to return
            
        Returns:
            List of suggestion strings ready to display
        """
        # Extract context
        context = self.extractor.extract(
            messages=messages,
            cv_names=cv_names,
            num_cvs=num_cvs
        )
        
        # Select suggestions
        suggestions = self.selector.select(context, count=count)
        
        # Fill templates
        filled = self.filler.fill(suggestions, context)
        
        logger.info(
            f"[SUGGESTION_ENGINE] Generated {len(filled)} suggestions "
            f"for query_type={context.last_query_type}"
        )
        
        return filled
    
    def reset(self):
        """Reset state for new session."""
        self.selector.reset()


# Singleton instance
_engine: Optional[SuggestionEngine] = None

def get_suggestion_engine() -> SuggestionEngine:
    """Get or create singleton SuggestionEngine."""
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine
```

---

#### ✅ **Tarea 3.2: Actualizar endpoint en routes_sessions.py**

**Archivo:** `backend/app/api/routes_sessions.py`

**Ubicación:** Reemplazar `get_suggested_questions()` (~línea 629)

```python
@router.get("/{session_id}/suggestions")
async def get_suggested_questions(
    session_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """
    Generate contextual suggestions based on conversation history.
    
    NEW: Uses SuggestionEngine with:
    - 9 query type banks (~120 suggestions)
    - Context extraction from conversation
    - Template filling with mentioned entities
    """
    import re
    
    def extract_name(filename: str) -> str:
        """Extract readable name from filename."""
        name = filename.replace('.pdf', '')
        name = re.sub(r'^[a-f0-9]{8}_', '', name)
        name = name.replace('_', ' ')
        parts = name.split()
        job_words = {'Senior', 'Junior', 'Lead', 'Head', 'Chief', 'Manager', 
                     'Director', 'Specialist', 'Engineer', 'Developer', 'Designer', 'Analyst'}
        if len(parts) >= 3 and parts[2] not in job_words and parts[2][0].isupper():
            return ' '.join(parts[:3])
        return ' '.join(parts[:2]) if len(parts) >= 2 else name[:20]
    
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    if not cvs:
        return {"suggestions": []}
    
    # Extract CV names
    cv_names = [
        extract_name(cv.get("filename", "") if isinstance(cv, dict) else cv.filename) 
        for cv in cvs
    ]
    num_cvs = len(cvs)
    
    # Get conversation history (REUTILIZAR infraestructura existente)
    messages = mgr.get_conversation_history(session_id, limit=10)
    
    # Convert ChatMessage to dict if needed
    history = []
    for msg in messages:
        if isinstance(msg, dict):
            history.append(msg)
        else:
            history.append({
                "role": msg.role,
                "content": msg.content,
                "structured_output": msg.structured_output if hasattr(msg, 'structured_output') else None
            })
    
    # Use SuggestionEngine
    from app.services.suggestion_engine import get_suggestion_engine
    engine = get_suggestion_engine()
    
    suggestions = engine.get_suggestions(
        messages=history,
        cv_names=cv_names,
        num_cvs=num_cvs,
        count=4
    )
    
    logger.info(
        f"[SUGGESTIONS] Generated {len(suggestions)} contextual suggestions "
        f"for session {session_id} ({num_cvs} CVs)"
    )
    
    return {"suggestions": suggestions}
```

---

#### ✅ **Tarea 3.3: Crear __init__.py**

**Archivo:** `backend/app/services/suggestion_engine/__init__.py`

```python
"""
Suggestion Engine - Dynamic contextual suggestions.

Usage:
    from app.services.suggestion_engine import get_suggestion_engine
    
    engine = get_suggestion_engine()
    suggestions = engine.get_suggestions(messages, cv_names, num_cvs)
"""
from .engine import SuggestionEngine, get_suggestion_engine
from .context_extractor import ContextExtractor, ExtractedContext
from .suggestion_selector import SuggestionSelector
from .template_filler import TemplateFiller
from .banks.base import Suggestion, SuggestionCategory, SuggestionBank

__all__ = [
    "SuggestionEngine",
    "get_suggestion_engine",
    "ContextExtractor",
    "ExtractedContext",
    "SuggestionSelector",
    "TemplateFiller",
    "Suggestion",
    "SuggestionCategory",
    "SuggestionBank",
]
```

---

### **Entregables Fase 3**
- [ ] `engine.py` con SuggestionEngine
- [ ] `__init__.py` con exports
- [ ] Endpoint actualizado usando SuggestionEngine
- [ ] Logs de generación de sugerencias

---

## **FASE 4: Testing y Refinamiento (2-3 horas)**

### Tareas

#### ✅ **Tarea 4.1: Crear tests unitarios**

**Archivo:** `backend/tests/test_suggestion_engine.py`

```python
"""
Tests for SuggestionEngine.
"""
import pytest
from app.services.suggestion_engine import (
    SuggestionEngine,
    ContextExtractor,
    SuggestionSelector,
    TemplateFiller,
    Suggestion,
    SuggestionCategory,
)


class TestContextExtractor:
    def test_extract_candidates_from_response(self):
        extractor = ContextExtractor()
        text = "**[Juan Pérez](cv:cv_abc123)** tiene experiencia en Python"
        candidates = extractor._extract_candidates(text)
        assert "Juan Pérez" in candidates
    
    def test_extract_skills_from_query(self):
        extractor = ContextExtractor()
        text = "Buscar candidatos con Python y React"
        skills = extractor._extract_skills(text)
        assert "python" in skills
        assert "react" in skills
    
    def test_extract_empty_context(self):
        extractor = ContextExtractor()
        context = extractor.extract([], [], 0)
        assert context.is_first_query
        assert context.last_query_type == "initial"


class TestSuggestionSelector:
    def test_select_from_search_bank(self):
        # Create minimal banks
        banks = {
            SuggestionCategory.SEARCH: [
                Suggestion("Test {skill}", SuggestionCategory.SEARCH, requires_skill=True),
            ],
            SuggestionCategory.INITIAL: [],
        }
        selector = SuggestionSelector(banks)
        
        from app.services.suggestion_engine.context_extractor import ExtractedContext
        context = ExtractedContext(
            last_query_type="search",
            mentioned_skills=["python"],
            num_cvs=2
        )
        
        selected = selector.select(context, count=1)
        assert len(selected) == 1
        assert "skill" in selected[0].text


class TestTemplateFiller:
    def test_fill_candidate_placeholder(self):
        filler = TemplateFiller()
        suggestions = [
            Suggestion("Perfil de {candidate_name}", SuggestionCategory.INITIAL, requires_candidate=True)
        ]
        
        from app.services.suggestion_engine.context_extractor import ExtractedContext
        context = ExtractedContext(
            mentioned_candidates=["Juan Pérez"],
            num_cvs=1
        )
        
        filled = filler.fill(suggestions, context)
        assert len(filled) == 1
        assert "Juan Pérez" in filled[0]


class TestSuggestionEngine:
    def test_full_flow_initial(self):
        engine = SuggestionEngine()
        suggestions = engine.get_suggestions(
            messages=[],
            cv_names=["Juan", "María"],
            num_cvs=2,
            count=4
        )
        assert len(suggestions) == 4
        assert all(isinstance(s, str) for s in suggestions)
    
    def test_full_flow_after_search(self):
        engine = SuggestionEngine()
        messages = [
            {"role": "user", "content": "Buscar candidatos con Python"},
            {
                "role": "assistant", 
                "content": "**[Juan Pérez](cv:cv_abc)** tiene Python",
                "structured_output": {"structure_type": "search"}
            }
        ]
        
        suggestions = engine.get_suggestions(
            messages=messages,
            cv_names=["Juan Pérez", "María García"],
            num_cvs=2,
            count=4
        )
        assert len(suggestions) == 4
```

---

#### ✅ **Tarea 4.2: Testing manual e2e**

**Tests manuales a realizar:**

1. **Sin contexto (primera query)**
   - Abrir sesión nueva
   - Ver sugerencias → deben ser del banco INITIAL
   
2. **Después de search**
   - Query: "Buscar candidatos con Python"
   - Ver sugerencias → deben incluir refinamientos de búsqueda
   
3. **Después de ranking**
   - Query: "Top 3 para backend"
   - Ver sugerencias → deben incluir análisis del #1, comparaciones
   
4. **Después de single_candidate**
   - Query: "Perfil de Juan Pérez"
   - Ver sugerencias → deben incluir red flags, comparaciones con otros
   
5. **Placeholders correctos**
   - Verificar que {candidate_name} se reemplaza correctamente
   - Verificar que {skill} se reemplaza correctamente

---

### **Entregables Fase 4**
- [ ] Tests unitarios pasando
- [ ] Tests e2e documentados
- [ ] Refinamiento de sugerencias según feedback

---

# PARTE 4: RESUMEN

## Archivos a Crear

| Archivo | Propósito | Líneas Est. |
|---------|-----------|-------------|
| `suggestion_engine/__init__.py` | Exports | ~20 |
| `suggestion_engine/engine.py` | Entry point | ~100 |
| `suggestion_engine/context_extractor.py` | Extrae contexto | ~150 |
| `suggestion_engine/suggestion_selector.py` | Selecciona sugerencias | ~120 |
| `suggestion_engine/template_filler.py` | Rellena placeholders | ~80 |
| `suggestion_engine/banks/__init__.py` | Exports bancos | ~20 |
| `suggestion_engine/banks/base.py` | Clases base | ~80 |
| `suggestion_engine/banks/initial_bank.py` | ~15 sugerencias | ~80 |
| `suggestion_engine/banks/search_bank.py` | ~15 sugerencias | ~80 |
| `suggestion_engine/banks/ranking_bank.py` | ~15 sugerencias | ~80 |
| `suggestion_engine/banks/comparison_bank.py` | ~15 sugerencias | ~80 |
| `suggestion_engine/banks/job_match_bank.py` | ~12 sugerencias | ~70 |
| `suggestion_engine/banks/team_build_bank.py` | ~12 sugerencias | ~70 |
| `suggestion_engine/banks/single_candidate_bank.py` | ~15 sugerencias | ~80 |
| `suggestion_engine/banks/risk_assessment_bank.py` | ~12 sugerencias | ~70 |
| `suggestion_engine/banks/verification_bank.py` | ~10 sugerencias | ~60 |
| **TOTAL** | **14 archivos** | **~1,200 líneas** |

## Archivos a Modificar

| Archivo | Cambio | Impacto |
|---------|--------|---------|
| `routes_sessions.py` | Reemplazar `get_suggested_questions()` | ~50 líneas |

## Timeline Estimado

| Fase | Horas | Descripción |
|------|-------|-------------|
| **1** | 3-4 | Infraestructura base |
| **2** | 4-5 | ~120 sugerencias en 9 bancos |
| **3** | 2-3 | Integración con API |
| **4** | 2-3 | Testing y refinamiento |
| **Total** | **12-15** | - |

## Comparativa Antes/Después

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Sugerencias totales** | 10 | ~120 |
| **Contextual** | ❌ | ✅ Basado en query_type |
| **Personalizado** | ❌ | ✅ Con nombres/skills |
| **Rotación** | Random | Por prioridad + historial |
| **Query types** | N/A | 9 bancos diferentes |
| **Placeholders** | ❌ | ✅ {candidate}, {skill}, {role} |
| **Deduplicación** | ❌ | ✅ Tracking de usados |

---

## Integración con Contexto Existente

**REUTILIZA completamente:**
- `get_conversation_history()` de SessionManager
- `structured_output.structure_type` de ChatMessage
- Patrones de extracción de candidatos existentes

**NO duplica:**
- Sistema de mensajes
- Almacenamiento de contexto
- Query type detection (usa el del Orchestrator)
