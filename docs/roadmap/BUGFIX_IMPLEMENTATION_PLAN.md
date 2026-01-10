# Bug Fix & Improvement Implementation Plan

> **Generated**: January 10, 2026  
> **Status**: Planning Phase  
> **Priority**: Critical fixes for production readiness

---

## Executive Summary

This document outlines a comprehensive implementation plan to address **21 identified issues** across the CV Screener application. Issues are categorized by severity and grouped into implementation phases to ensure systematic resolution.

### Issue Breakdown

| Priority | Category | Count | Estimated Effort |
|----------|----------|-------|------------------|
| 🔴 Critical | Logic/Coherence Bugs | 6 | 3-4 days |
| 🟠 High | CV Parsing Issues | 5 | 2-3 days |
| 🟡 Medium | UI/UX Format Issues | 6 | 2 days |
| 🟢 Low | Content/Text Improvements | 4 | 1 day |

**Total Estimated Effort**: 8-10 days

---

## Phase 1: Critical Logic & Coherence Bugs

### 1.1 Ranking vs Conclusion Inconsistency

**Issue**: The conclusion text contradicts the visual ranking displayed.

**Example**:
- UI Ranking shows: Amir Al-Farsi #1 (12 years)
- Conclusion states: "Liam van der Merwe is the candidate with the most total experience"

**Root Cause**: LLM generates conclusion independently from the structured ranking data.

**Solution**:
```
1. Modify output processor to inject ranking results INTO the prompt context
2. Add validation layer that cross-checks conclusion mentions against ranking order
3. If mismatch detected, regenerate conclusion using ranking data as ground truth
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/ranking_structure.py`
- `backend/app/services/llm_service.py`

**Acceptance Criteria**:
- [ ] Conclusion text always references the same #1 candidate shown in ranking
- [ ] Automated test validates ranking-conclusion alignment
- [ ] No contradictions in 50 consecutive test queries

---

### 1.2 Top Candidate Context Drift

**Issue**: "Top candidate" changes between questions without explanation.

**Example**:
- Q1: Top = Amir Al-Farsi (12 yrs)
- Q9: "Is top candidate 10 years?" → References Aisha Tan Pizza

**Root Cause**: System doesn't maintain conversational context for "top candidate" definition.

**Solution**:
```
1. Implement conversation state tracking for key entities:
   - top_candidate_id
   - top_candidate_name
   - ranking_context
2. When user references "top candidate", resolve to stored value
3. Add explicit clarification if ranking criteria changes
```

**Files to Modify**:
- `backend/app/services/conversation_context.py` (create if needed)
- `backend/app/api/routes/chat.py`

**Acceptance Criteria**:
- [ ] "Top candidate" resolves consistently within a session
- [ ] System explains if ranking criteria changes
- [ ] Context persists across follow-up questions

---

### 1.3 Red Flags: Zero Experience = Low Risk

**Issue**: Candidates with 0 years experience are marked as "low-risk".

**Example**:
```
"Lucien Moreau presents a low-risk profile. With 0 years of experience..."
```

**Root Cause**: Risk assessment logic doesn't flag missing/zero experience as a risk factor.

**Solution**:
```python
# Add experience validation in risk assessment
def calculate_risk_level(candidate):
    risks = []
    
    # NEW: Flag zero/missing experience
    if candidate.total_experience_years == 0:
        risks.append({
            "type": "experience",
            "severity": "caution",  # or "risk" depending on role requirements
            "message": "No verifiable work experience"
        })
    
    # Existing checks...
    if candidate.job_hopping_score > 0.5:
        risks.append(...)
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/red_flags_structure.py`
- `backend/app/services/risk_assessment.py` (if exists)

**Acceptance Criteria**:
- [ ] Zero experience triggers "Caution" or "Risk" flag
- [ ] Risk assessment message accurately reflects the concern
- [ ] UI displays appropriate warning indicator

---

### 1.4 Top 5 List Mismatch

**Issue**: Ranking UI shows different candidates than conclusion text.

**Example**:
- UI: Amir Al-Farsi, Lena Schmidt, Amir Hassan, Aisha Tan Pizza, Liam van der Merwe
- Conclusion: "Top 5 are Javier Morales, Liam van der Merwe, Ingrid Larsson..."

**Root Cause**: Same as 1.1 - LLM conclusion not bound to structured output.

**Solution**:
```
1. Generate conclusion FROM the ranking results, not independently
2. Template-based conclusion generation:
   "The top {n} candidates are {names_from_ranking}. {criteria_explanation}"
3. Remove LLM freedom to name different candidates in conclusion
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/ranking_structure.py`
- `backend/app/prompts/ranking_prompts.py`

**Acceptance Criteria**:
- [ ] Conclusion names match UI ranking exactly
- [ ] Order in conclusion matches ranking order
- [ ] 100% alignment in automated tests

---

### 1.5 Job Match Best vs Conclusion Mismatch

**Issue**: Best match card shows one candidate, conclusion recommends another.

**Example**:
- Best Match Card: Lena Schmidt (75%)
- Conclusion: "Aisha Okafor is the best fit"

**Root Cause**: Conclusion generated before/without structured match results.

**Solution**:
```
1. Enforce conclusion generation AFTER match scoring
2. Pass match_scores to conclusion template
3. Conclusion must reference highest-scoring candidate
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/job_match_structure.py`

**Acceptance Criteria**:
- [ ] Conclusion always names the highest-match-score candidate
- [ ] If tie, conclusion mentions both candidates
- [ ] Validation test confirms alignment

---

### 1.6 Verification Query Logic Error

**Issue**: System says "NOT_FOUND (30% confidence)" but concludes "Yes, it's true".

**Example**:
```
NOT_FOUND - No evidence found in CV to verify: 10 years experience?
Conclusion: Yes, the top candidate has 10 years of experience.
```

**Root Cause**: Conclusion logic not conditioned on verification result.

**Solution**:
```python
def generate_verification_conclusion(verification_result):
    if verification_result.status == "NOT_FOUND":
        return f"Unable to verify. No evidence found in CV for: {claim}"
    elif verification_result.status == "VERIFIED":
        return f"Yes, verified. {evidence_summary}"
    elif verification_result.status == "CONTRADICTED":
        return f"No, contradicted. {contradiction_details}"
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/verification_structure.py`

**Acceptance Criteria**:
- [ ] NOT_FOUND → Conclusion = "Unable to verify" or "No evidence"
- [ ] VERIFIED → Conclusion = "Yes" + evidence
- [ ] CONTRADICTED → Conclusion = "No" + contradiction
- [ ] Confidence score influences conclusion wording

---

## Phase 2: CV Parsing Issues

### 2.1 Corrupted Candidate Names

**Issue**: Names contain invalid data (e.g., "Aisha Tan Pizza").

**Root Cause**: PDF/text extraction merging adjacent fields.

**Solution**:
```
1. Add name validation regex: ^[A-Za-z\-'\s]+$
2. Implement name cleaning pipeline:
   - Remove non-name words (food, objects, etc.)
   - Cross-reference with common name databases
3. Flag suspicious names for manual review
```

**Files to Modify**:
- `backend/app/services/cv_parser/` (parsing module)
- `scripts/reindex_cvs.py`

**Acceptance Criteria**:
- [ ] No food/object words in candidate names
- [ ] Names pass validation regex
- [ ] Suspicious names flagged in logs

---

### 2.2 Skills Parsing Errors

**Issue**: Skills contain garbage data, wrong categorization, spaced letters.

**Examples**:
- "E D U C A T I O N" (spaces between letters)
- "Master Of Arts In" (education as skill)
- "Local Fashion House (Early" (company name fragment)

**Solution**:
```
1. Add skill cleaning pipeline:
   - Remove strings with single-letter spacing
   - Filter against education/company name patterns
   - Validate against known skill taxonomies
2. Implement skill categorization validation
3. Add minimum skill length threshold (3+ words or known term)
```

**Files to Modify**:
- `backend/app/services/cv_parser/skills_extractor.py`
- `backend/app/models/cv_chunk.py`

**Acceptance Criteria**:
- [ ] No spaced-letter strings in skills
- [ ] Education items excluded from skills
- [ ] Company names excluded from skills
- [ ] Skills are recognizable professional terms

---

### 2.3 Top Skills Aggregation Errors

**Issue**: Pool-wide "Top Skills" includes non-skills.

**Examples**:
- "Master Of Arts In: 1 (4%)"
- "Local Fashion House (Early: 1 (4%)"
- "& Analysis Styling Intern: 1 (4%)"

**Solution**:
```
1. Pre-filter skill list before aggregation
2. Apply skill validation to aggregated results
3. Minimum occurrence threshold (>1) to avoid noise
4. Blacklist common non-skill patterns
```

**Files to Modify**:
- `backend/app/services/analytics/skill_aggregator.py`
- `frontend/src/components/TalentPoolOverview.jsx` (if client-side)

**Acceptance Criteria**:
- [ ] Top skills are all valid professional skills
- [ ] No education, company names, or fragments
- [ ] Aggregation uses validated skill data only

---

### 2.4 Career Trajectory Formatting

**Issue**: Timeline shows duplicates, URLs mixed with companies, "Not specified" displayed.

**Example**:
```
Strategic leadership... — Nordic Learning Solutions
→ Strategic leadership... Amir Al-Farsi — TechGrowth AB
→ Not specified EduTech Innovations — amiralfarsi.com
```

**Solution**:
```
1. Deduplicate consecutive identical titles
2. Separate URL extraction from company parsing
3. Hide entries with "Not specified" or empty roles
4. Validate company vs URL field assignment
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/single_candidate_structure.py`
- `frontend/src/components/CareerTimeline.jsx`

**Acceptance Criteria**:
- [ ] No duplicate consecutive entries
- [ ] URLs appear in dedicated field, not mixed with company
- [ ] "Not specified" entries hidden or marked differently
- [ ] Clean, readable timeline format

---

### 2.5 Zero Experience for Experienced Candidates

**Issue**: Many candidates show 0 years when they clearly have experience.

**Root Cause**: Experience calculation failing or field not populated during parsing.

**Solution**:
```
1. Audit experience calculation logic
2. If dates available, calculate from work history
3. If no dates, estimate from position count and typical tenure
4. Add fallback: "Experience data unavailable" vs showing 0
```

**Files to Modify**:
- `backend/app/services/cv_parser/experience_calculator.py`
- `backend/app/services/chunk_processor.py`

**Acceptance Criteria**:
- [ ] Candidates with work history show >0 years
- [ ] Clear distinction between "0 years" and "unknown"
- [ ] Experience calculated from available date ranges

---

## Phase 3: UI/UX Format Issues

### 3.1 Negative Percentage Display

**Issue**: Rankings show confusing negative percentages (e.g., "-1%", "-11%").

**Solution**:
```
Option A: Remove delta column entirely
Option B: Label clearly: "vs #1: -11%"
Option C: Show only absolute score
```

**Files to Modify**:
- `frontend/src/components/RankingTable.jsx`

**Acceptance Criteria**:
- [ ] No unexplained negative values
- [ ] Clear labeling if deltas shown
- [ ] User understands what numbers mean

---

### 3.2 Missing Names in Conclusions

**Issue**: Conclusions have missing name references: "has 16 years of experience..." (who?)

**Solution**:
```
1. Validate conclusion text for orphaned pronouns/verbs
2. Ensure every metric reference includes candidate name
3. Template: "{name} has {X} years of experience."
```

**Files to Modify**:
- `backend/app/services/output_processor/conclusion_generator.py`

**Acceptance Criteria**:
- [ ] No orphaned subject references
- [ ] Every metric tied to explicit candidate name
- [ ] Grammar validation on conclusion text

---

### 3.3 Team Builder: Missing Member List

**Issue**: Shows team stats but not WHO is on the team.

**Current**:
```
Team Size: 3 members
Combined Exp: 52 years
```

**Should Be**:
```
Team Size: 3 members
- Amir Al-Farsi (12 yrs)
- Lena Schmidt (15 yrs)  
- Liam van der Merwe (16 yrs)
Combined Exp: 43 years
```

**Solution**:
```
1. Add team_members array to team composition output
2. Display member cards/list in UI
3. Show individual contributions to team metrics
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/team_structure.py`
- `frontend/src/components/TeamComposition.jsx`

**Acceptance Criteria**:
- [ ] Team members listed by name
- [ ] Individual experience shown
- [ ] Combined stats match sum of individuals

---

### 3.4 Search Results vs Conclusion Order Mismatch

**Issue**: Search results show one order, conclusion lists different order.

**Solution**:
```
1. Conclusion order derived from search ranking
2. Top matches in conclusion = top matches in UI
3. Or: explicitly state different ordering criteria
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/search_structure.py`

**Acceptance Criteria**:
- [ ] Conclusion order matches or explains difference from UI order
- [ ] Top 3 in conclusion = Top 3 in search results

---

### 3.5 Candidate Count Mismatch

**Issue**: Header says "36 CVs" but experience distribution shows 28 total.

**Solution**:
```
1. Audit count sources
2. Use consistent count variable throughout
3. Show filtered vs total: "28 of 36 CVs with experience data"
```

**Files to Modify**:
- `frontend/src/components/TalentPoolOverview.jsx`
- `backend/app/api/routes/analytics.py`

**Acceptance Criteria**:
- [ ] Counts are consistent across UI
- [ ] Filtered counts explained
- [ ] Total always matches header

---

### 3.6 Match Requirements Count Error

**Issue**: Shows "(1 requirements)" but "2 met" for same candidate.

**Solution**:
```
1. Fix pluralization: "1 requirement" vs "2 requirements"
2. Ensure requirements count matches "met" denominator
3. Display: "2 of 3 requirements met"
```

**Files to Modify**:
- `frontend/src/components/MatchScores.jsx`
- `backend/app/services/output_processor/structures/job_match_structure.py`

**Acceptance Criteria**:
- [ ] Grammar correct (singular/plural)
- [ ] "X met" never exceeds total requirements
- [ ] Clear fraction format: "X of Y met"

---

## Phase 4: Content & Text Improvements

### 4.1 Risk Assessment Always "Clear"

**Issue**: All indicators show "Clear" even when there are real concerns.

**Solution**:
```
1. Implement actual risk evaluation per category
2. Experience: Flag if < 2 years for senior roles
3. Job Hopping: Flag if score > 0.5
4. Gaps: Flag if > 6 months unexplained
5. Display appropriate status: Clear / Caution / Risk
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/risk_assessment_structure.py`

**Acceptance Criteria**:
- [ ] Each category independently evaluated
- [ ] Real flags displayed when criteria met
- [ ] "Clear" only when actually clear

---

### 4.2 Education Field Truncation

**Issue**: Education shows "Master of Arts in" (incomplete).

**Solution**:
```
1. Extract full education string
2. Parse degree + field + institution
3. Fallback: show raw text if parsing fails
4. Never display truncated values
```

**Files to Modify**:
- `backend/app/services/cv_parser/education_extractor.py`

**Acceptance Criteria**:
- [ ] Full degree title displayed
- [ ] Field of study included
- [ ] No truncated strings

---

### 4.3 Verification Confidence Alignment

**Issue**: Low confidence (30%) but definitive conclusion ("Yes").

**Solution**:
```
Confidence-based response templates:
- 80-100%: "Yes/No, confirmed by {evidence}"
- 50-79%: "Likely yes/no, based on {partial_evidence}"
- 30-49%: "Unable to confirm. Limited evidence suggests..."
- <30%: "Cannot verify. No sufficient evidence found."
```

**Files to Modify**:
- `backend/app/services/output_processor/structures/verification_structure.py`

**Acceptance Criteria**:
- [ ] Conclusion language matches confidence level
- [ ] Low confidence = hedged language
- [ ] High confidence = definitive statements

---

### 4.4 Consistent Language & Tone

**Issue**: Mixed formality and style across responses.

**Solution**:
```
1. Define style guide for responses
2. Apply consistent tone templates
3. Review all prompt templates for consistency
```

**Files to Modify**:
- `backend/app/prompts/*.py`

**Acceptance Criteria**:
- [ ] Uniform professional tone
- [ ] Consistent header/section naming
- [ ] No jarring style changes between responses

---

## Implementation Schedule

```
Week 1: Phase 1 (Critical Bugs)
├── Day 1-2: Issues 1.1, 1.4, 1.5 (Ranking-Conclusion alignment)
├── Day 3: Issues 1.2 (Context tracking)
├── Day 4: Issues 1.3, 1.6 (Risk & Verification logic)
└── Day 5: Testing & validation

Week 2: Phase 2 (Parsing) + Phase 3 (UI/UX)
├── Day 1-2: Issues 2.1-2.3 (Name & Skills parsing)
├── Day 2-3: Issues 2.4-2.5 (Timeline & Experience)
├── Day 4: Issues 3.1-3.3 (UI fixes)
└── Day 5: Issues 3.4-3.6 + Testing

Week 3: Phase 4 (Content) + Final QA
├── Day 1: Issues 4.1-4.2 (Risk assessment, Education)
├── Day 2: Issues 4.3-4.4 (Verification, Tone)
├── Day 3-4: Integration testing
└── Day 5: Documentation & deployment
```

---

## Testing Strategy

### Unit Tests
- Each fix includes corresponding test cases
- Test both positive and negative scenarios
- Validate edge cases (empty data, null values)

### Integration Tests
- End-to-end query tests for all issue types
- Conversation context persistence tests
- Ranking consistency tests (100 queries)

### Regression Tests
- Ensure fixes don't break existing functionality
- Performance benchmarks maintained
- UI snapshot tests for format changes

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Ranking-Conclusion alignment | ~40% | 100% |
| Context consistency (follow-ups) | ~60% | 95%+ |
| Valid skills rate | ~70% | 95%+ |
| Risk assessment accuracy | ~50% | 90%+ |
| Zero-experience false positives | ~30% | <5% |

---

## Rollback Plan

Each phase has independent rollback capability:
1. Feature flags for new logic
2. Database migrations reversible
3. Previous prompt versions preserved
4. UI changes toggleable via config

---

## Appendix: File Reference

### Backend Files
```
backend/app/services/output_processor/structures/
├── ranking_structure.py
├── job_match_structure.py
├── verification_structure.py
├── red_flags_structure.py
├── team_structure.py
├── search_structure.py
└── single_candidate_structure.py

backend/app/services/
├── llm_service.py
├── conversation_context.py
├── risk_assessment.py
└── cv_parser/
    ├── skills_extractor.py
    ├── experience_calculator.py
    └── education_extractor.py

backend/app/prompts/
└── *.py (all prompt templates)
```

### Frontend Files
```
frontend/src/components/
├── RankingTable.jsx
├── TeamComposition.jsx
├── CareerTimeline.jsx
├── MatchScores.jsx
└── TalentPoolOverview.jsx
```

---

*Document maintained by: Development Team*  
*Last updated: January 10, 2026*
