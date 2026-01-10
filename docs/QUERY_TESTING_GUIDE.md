# 🧪 Query Testing Guide - All Structure Types

This document contains test queries for each structure type. Copy and paste these queries to verify that the correct structure is being used.

> **How to verify**: Check the logs for `[ORCHESTRATOR] Using <StructureName>` or look at the `STRUCTURE_ROUTING` event in debug logs.

---

## 1. 🔍 SEARCH Structure (Default)

**Expected log**: `[ORCHESTRATOR] Using SearchStructure`

```
Who has experience in marketing?
```

```
Find candidates with Python skills
```

```
Show me everyone with more than 5 years of experience
```

```
List all candidates from Spain
```

```
Who speaks French?
```

```
Which candidates have worked in finance?
```

```
Find people with MBA degrees
```

```
Who has leadership experience?
```

---

## 2. 👤 SINGLE_CANDIDATE Structure

**Expected log**: `[ORCHESTRATOR] Using SingleCandidateStructure`

```
Give me the full profile of the top candidate
```

```
Tell me everything about the best match
```

```
Analyze the first candidate in detail
```

```
Full profile of the most experienced person
```

```
Give me complete information about the senior developer
```

```
Everything about the candidate with the highest score
```

```
All about the marketing specialist
```

---

## 3. ⚠️ RED_FLAGS / Risk Assessment Structure

**Expected log**: `[ORCHESTRATOR] Using RiskAssessmentStructure`

```
Show me the red flags in the candidate pool
```

```
Analyze job hopping patterns
```

```
Are there any employment gaps?
```

```
Do a risk assessment of the candidates
```

```
Show warning signs for hiring
```

```
Analyze career stability
```

```
Make a risk assessment of the top candidate
```

```
Check for job hopping behavior
```

---

## 4. 🏆 RANKING Structure

**Expected log**: `[ORCHESTRATOR] Using RankingStructure`

```
Rank all candidates by experience
```

```
Who is the best for a senior role?
```

```
Give me the top 5 candidates
```

```
Order candidates by skills
```

```
Who would be the best leader?
```

```
Sort by years of experience
```

```
Show me the ranking for technical skills
```

```
Who has the best leadership potential?
```

---

## 5. ⚖️ COMPARISON Structure

**Expected log**: `[ORCHESTRATOR] Using ComparisonStructure`

```
Compare the top 2 candidates
```

```
What are the differences between the senior candidates?
```

```
Senior vs Junior candidates analysis
```

```
Compare marketing and sales experience
```

```
Which is better between the two finalists?
```

```
Contrast technical vs business candidates
```

---

## 6. 🎯 JOB_MATCH Structure

**Expected log**: `[ORCHESTRATOR] Using JobMatchStructure`

```
Who fits best for a project manager position?
```

```
Match candidates to the senior developer requirements
```

```
Who is suitable for a team lead role?
```

```
Find the best match for the job description
```

```
Who meets the requirements for a data analyst?
```

```
Which candidate fits the marketing director position?
```

---

## 7. 👥 TEAM_BUILD Structure

**Expected log**: `[ORCHESTRATOR] Using TeamBuildStructure`

```
Build a team with the top 3 candidates
```

```
Create a development team from the pool
```

```
Form a complementary team for the project
```

```
Assemble a team with diverse skills
```

```
Make a team using the best matches
```

```
Build a balanced team for the startup
```

---

## 8. ✅ VERIFICATION Structure

**Expected log**: `[ORCHESTRATOR] Using VerificationStructure`

```
Verify if anyone has worked at Google
```

```
Confirm the education credentials
```

```
Check if the candidate has AWS certification
```

```
Validate the leadership claims
```

```
Did anyone work at Microsoft?
```

```
Is it true that the top candidate has 10 years experience?
```

---

## 9. 📊 SUMMARY Structure

**Expected log**: `[ORCHESTRATOR] Using SummaryStructure`

```
Give me a summary of the candidate pool
```

```
Overview of all candidates
```

```
Show me the statistics
```

```
How many candidates have technical skills?
```

```
What is the experience distribution?
```

```
General view of the talent pool
```

```
Pool overview and stats
```

---

## 🔄 Testing Workflow

1. **Start fresh session** with CVs loaded
2. **Copy a query** from each section above
3. **Send the query** to the chat
4. **Check the logs** for the structure being used:
   - Look for: `[ORCHESTRATOR] Using <StructureName>`
   - Or check debug log: `STRUCTURE_ROUTING` event with `query_type`

### Expected Log Examples

```
# Single Candidate
[ORCHESTRATOR] Using SingleCandidateStructure for <name>

# Risk Assessment  
[ORCHESTRATOR] Using RiskAssessmentStructure for <name>

# Search (default)
[ORCHESTRATOR] Using SearchStructure

# Ranking
[ORCHESTRATOR] Using RankingStructure

# Team Build
[ORCHESTRATOR] Using TeamBuildStructure
```

---

## ⚠️ Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Always shows "search" | Query doesn't match patterns | Use exact keywords from patterns |
| Single candidate needs name | No candidate context | Refer to "the top candidate" or similar |
| Red flags needs candidate | Must be about specific person | Add context like "of the candidates" |

---

## 📝 Notes

- **search** is the default fallback when no patterns match
- **single_candidate** requires either a name in the query OR context from previous messages
- **red_flags** triggers on specific keywords like "red flag", "job hopping", "employment gap"
- **team_build** takes priority over **ranking** if "team" is mentioned
