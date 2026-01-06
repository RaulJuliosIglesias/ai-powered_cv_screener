/**
 * Parser for single candidate profile output from LLM
 * 
 * Extracts structured data from the markdown output to render
 * in the SingleCandidateProfile component.
 */

/**
 * Detect if this is a single candidate response
 * @param {string} content - Raw LLM output
 * @returns {boolean}
 */
export const isSingleCandidateResponse = (content) => {
  if (!content) return false;
  
  const singleCandidateIndicators = [
    /## 👤\s*\*\*\[/,                          // Header format
    /### 📊 Candidate Highlights/,             // Highlights section
    /### 💼 Career Trajectory/,                // Career section
    /### 🛠️ Skills Snapshot/,                 // Skills section
    /SINGLE CANDIDATE PROFILE/i,               // Template marker
    /CRITICAL DATA EXTRACTION RULES/i,         // New template marker
  ];
  
  const matchCount = singleCandidateIndicators.filter(pattern => pattern.test(content)).length;
  return matchCount >= 2;
};

/**
 * Detect if this is a standalone Risk Assessment response for a SINGLE candidate
 * (not embedded in SingleCandidateProfile, and not a multi-candidate query)
 * @param {string} content - Raw LLM output
 * @returns {boolean}
 */
export const isRiskAssessmentResponse = (content) => {
  if (!content) return false;
  
  // Risk Assessment indicators
  const riskIndicators = [
    /### 🚩 Risk Analysis/,                    // Risk Analysis header
    /RED FLAGS ANALYSIS/i,                      // Template marker
    /Risk factors identified for/i,             // Risk statement
    /No significant red flags detected/i,       // Clean profile statement
    /### ⚠️ Risk Assessment/,                  // Risk Assessment section
  ];
  
  const hasRiskIndicators = riskIndicators.filter(pattern => pattern.test(content)).length >= 2;
  
  // Make sure it's NOT a full SingleCandidateProfile
  const isNotFullProfile = !isSingleCandidateResponse(content);
  
  // CRITICAL: Check if this is a MULTI-CANDIDATE response
  // If multiple candidates are mentioned, this is NOT a single-candidate risk assessment
  const multiCandidateIndicators = [
    /all candidates/i,
    /multiple candidates/i,
    /each candidate/i,
    /todos los candidatos/i,
    // Count candidate name patterns - if more than one cv: link, it's multi-candidate
  ];
  
  const isMultiCandidate = multiCandidateIndicators.some(pattern => pattern.test(content));
  
  // Also check: if there are multiple cv: links, it's likely multi-candidate
  const cvLinkMatches = content.match(/\(cv:cv_[a-zA-Z0-9_-]+\)/g) || [];
  const uniqueCvIds = [...new Set(cvLinkMatches)];
  const hasMultipleCandidates = uniqueCvIds.length > 1;
  
  // Only return true for SINGLE candidate risk assessments
  return hasRiskIndicators && isNotFullProfile && !isMultiCandidate && !hasMultipleCandidates;
};

/**
 * Parse Risk Assessment standalone response
 * @param {string} content - Raw LLM output
 * @returns {{ candidateName: string, cvId: string, riskAnalysis: string, riskAssessment: Array, conclusion: string }}
 */
export const parseRiskAssessmentResponse = (content) => {
  if (!content) return null;
  
  // Extract candidate info from risk analysis header
  // Pattern: ### 🚩 Risk Analysis for **[Name](cv:cv_xxx)**
  const headerPattern = /### 🚩 Risk Analysis for \*\*\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*/;
  const headerMatch = content.match(headerPattern);
  
  let candidateName = 'Unknown Candidate';
  let cvId = '';
  
  if (headerMatch) {
    candidateName = headerMatch[1].trim();
    cvId = headerMatch[2].trim();
  }
  
  // Extract risk analysis text (between header and Risk Assessment table)
  let riskAnalysis = '';
  const analysisStart = content.indexOf('### 🚩 Risk Analysis');
  if (analysisStart !== -1) {
    const analysisEnd = content.indexOf('### ⚠️ Risk Assessment', analysisStart);
    if (analysisEnd !== -1) {
      riskAnalysis = content.substring(analysisStart, analysisEnd).trim();
      // Remove the header itself
      riskAnalysis = riskAnalysis.replace(/### 🚩 Risk Analysis[^\n]*\n/, '').trim();
    }
  }
  
  // Extract Risk Assessment table using existing function
  const riskAssessment = extractRiskAssessment(content);
  
  // Extract conclusion
  const { assessment } = extractAssessment(content);
  
  return {
    candidateName,
    cvId,
    riskAnalysis,
    riskAssessment,
    conclusion: assessment
  };
};

/**
 * Extract candidate name and CV ID from header
 * @param {string} content 
 * @returns {{ name: string, cvId: string } | null}
 */
export const extractCandidateInfo = (content) => {
  if (!content) return null;
  
  // Pattern: ## 👤 **[Name](cv:cv_xxx)**
  const headerPattern = /## 👤\s*\*\*\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*/;
  const match = content.match(headerPattern);
  
  if (match) {
    return {
      name: match[1].trim(),
      cvId: match[2].trim()
    };
  }
  
  // Fallback: Try to find from other patterns
  const fallbackPattern = /\*\*\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*/;
  const fallbackMatch = content.match(fallbackPattern);
  
  if (fallbackMatch) {
    return {
      name: fallbackMatch[1].trim(),
      cvId: fallbackMatch[2].trim()
    };
  }
  
  return null;
};

/**
 * Extract summary paragraph (first paragraph after header)
 * @param {string} content 
 * @returns {string | null}
 */
export const extractSummary = (content) => {
  if (!content) return null;
  
  // Find content between header and first --- or ### section
  const headerEnd = content.indexOf('## 👤');
  if (headerEnd === -1) return null;
  
  const afterHeader = content.substring(headerEnd);
  const lines = afterHeader.split('\n');
  
  let summaryLines = [];
  let started = false;
  
  for (const line of lines) {
    // Skip the header line
    if (line.startsWith('## 👤')) {
      started = true;
      continue;
    }
    
    // Stop at next section or separator
    if (started && (line.startsWith('---') || line.startsWith('###'))) {
      break;
    }
    
    // Collect non-empty lines
    if (started && line.trim()) {
      summaryLines.push(line.trim());
    }
  }
  
  if (summaryLines.length === 0) return null;
  
  let summary = summaryLines.join(' ');
  
  // FIX: Clean up broken markdown links caused by line breaks
  // Pattern: **[Name](cv: cv_xxx)** -> **[Name](cv:cv_xxx)**
  // The space after "cv:" breaks the link
  summary = summary.replace(/\]\(cv:\s+(cv_[a-f0-9]+)\)/gi, '](cv:$1)');
  
  // Also fix any other whitespace issues in cv links
  summary = summary.replace(/\]\(\s*cv:\s*/gi, '](cv:');
  
  return summary;
};

/**
 * Extract highlights table
 * @param {string} content 
 * @returns {Array<{ category: string, value: string }>}
 */
export const extractHighlights = (content) => {
  if (!content) return [];
  
  const highlights = [];
  
  // Find the highlights section
  const highlightsStart = content.indexOf('### 📊 Candidate Highlights');
  if (highlightsStart === -1) return [];
  
  // CRITICAL: Find boundary - stop at next section (--- or ###)
  // This prevents capturing rows from Skills Snapshot table
  const afterStart = content.substring(highlightsStart);
  const nextSeparator = afterStart.indexOf('\n---\n');
  const nextSection = afterStart.indexOf('\n###');
  
  let boundary = afterStart.length;
  if (nextSeparator !== -1 && nextSeparator < boundary) boundary = nextSeparator;
  if (nextSection !== -1 && nextSection < boundary) boundary = nextSection;
  
  const highlightsSection = afterStart.substring(0, boundary);
  
  // Find the table rows - ONLY within Highlights section
  // Pattern: | **emoji Category** | Value |
  const rowPattern = /\|\s*\*\*([^|]+)\*\*\s*\|\s*([^|]+)\|/g;
  let match;
  
  // Only extract the 5 expected highlight categories
  const validCategories = ['current role', 'total experience', 'top achievement', 'core expertise', 'education'];
  
  while ((match = rowPattern.exec(highlightsSection)) !== null) {
    const category = match[1].trim();
    const value = match[2].trim();
    
    // Skip header row
    if (category.toLowerCase().includes('category') || value.toLowerCase().includes('key information')) {
      continue;
    }
    
    // Skip separator row
    if (category.includes('---') || value.includes('---')) {
      continue;
    }
    
    // Only include valid highlight categories (ignore skill rows that might slip through)
    const categoryLower = category.toLowerCase();
    const isValidHighlight = validCategories.some(vc => categoryLower.includes(vc.split(' ')[0]));
    
    if (category && value && value !== '[' && !value.startsWith('[') && isValidHighlight) {
      highlights.push({ category, value });
    }
  }
  
  return highlights;
};

/**
 * Extract career trajectory - captures ALL positions
 * @param {string} content 
 * @returns {Array<{ title: string, company: string, period: string, achievement: string }>}
 */
export const extractCareer = (content) => {
  if (!content) return [];
  
  const career = [];
  
  // Find career section
  const careerStart = content.indexOf('### 💼 Career Trajectory');
  if (careerStart === -1) return [];
  
  // Find end of career section (next ### or --- followed by ###)
  let careerEnd = content.indexOf('### 🛠️', careerStart + 1);
  if (careerEnd === -1) careerEnd = content.indexOf('### 📜', careerStart + 1);
  if (careerEnd === -1) careerEnd = content.indexOf(':::conclusion', careerStart + 1);
  if (careerEnd === -1) careerEnd = content.length;
  
  const careerSection = content.substring(careerStart, careerEnd);
  
  const lines = careerSection.split('\n');
  let currentJob = null;
  
  for (const line of lines) {
    // Multiple patterns for job titles
    // Pattern 1: **Title** — *Company* (Year-Year)
    // Pattern 2: **Title** - *Company* (Year)
    // Pattern 3: **[Title]** at Company
    const jobPatterns = [
      /\*\*([^*\[\]]+)\*\*\s*[—–-]\s*\*([^*]+)\*\s*(?:\(([^)]+)\))?/,
      /\*\*\[?([^\]*]+)\]?\*\*\s+(?:at|@|-|—)\s+\*?([^*\n(]+)\*?\s*(?:\(([^)]+)\))?/,
    ];
    
    let jobMatch = null;
    for (const pattern of jobPatterns) {
      jobMatch = line.match(pattern);
      if (jobMatch) break;
    }
    
    if (jobMatch) {
      // Save previous job if exists
      if (currentJob) {
        career.push(currentJob);
      }
      currentJob = {
        title: jobMatch[1].trim(),
        company: jobMatch[2].trim(),
        period: jobMatch[3]?.trim() || '',
        achievement: ''
      };
    } else if (currentJob) {
      // Look for achievement line (→ or > or - followed by text)
      const achieveMatch = line.match(/^[\s]*[→>•\-]\s*(.+)/);
      if (achieveMatch && achieveMatch[1].trim().length > 10) {
        // Only take first achievement if we don't have one yet
        if (!currentJob.achievement) {
          currentJob.achievement = achieveMatch[1].trim();
        }
      }
    }
  }
  
  // Don't forget the last job
  if (currentJob) {
    career.push(currentJob);
  }
  
  return career;
};

/**
 * Extract skills snapshot
 * @param {string} content 
 * @returns {Array<{ area: string, details: string }>}
 */
export const extractSkills = (content) => {
  if (!content) return [];
  
  const skills = [];
  
  // Find skills section
  const skillsStart = content.indexOf('### 🛠️ Skills Snapshot');
  if (skillsStart === -1) return [];
  
  // Find end of skills section
  let skillsEnd = content.indexOf('###', skillsStart + 1);
  if (skillsEnd === -1) skillsEnd = content.indexOf(':::', skillsStart + 1);
  if (skillsEnd === -1) skillsEnd = content.length;
  
  const skillsSection = content.substring(skillsStart, skillsEnd);
  
  // Pattern for table rows: | **Category** | Details |
  const rowPattern = /\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|/g;
  let match;
  
  while ((match = rowPattern.exec(skillsSection)) !== null) {
    const area = match[1].trim();
    const details = match[2].trim();
    
    // Skip header/separator rows
    if (area.toLowerCase().includes('skill') && details.toLowerCase().includes('details')) continue;
    if (area.includes('---')) continue;
    if (area.startsWith('[')) continue;
    
    if (area && details) {
      skills.push({ area, details });
    }
  }
  
  return skills;
};

/**
 * Extract credentials
 * @param {string} content 
 * @returns {string[]}
 */
export const extractCredentials = (content) => {
  if (!content) return [];
  
  const credentials = [];
  
  // Find credentials section
  const credStart = content.indexOf('### 📜 Credentials');
  if (credStart === -1) return [];
  
  // Find end
  let credEnd = content.indexOf('###', credStart + 1);
  if (credEnd === -1) credEnd = content.indexOf(':::', credStart + 1);
  if (credEnd === -1) credEnd = content.length;
  
  const credSection = content.substring(credStart, credEnd);
  
  // Extract bullet points
  const bulletPattern = /^[-•*]\s*(.+)$/gm;
  let match;
  
  while ((match = bulletPattern.exec(credSection)) !== null) {
    const cred = match[1].trim();
    if (cred && !cred.startsWith('[Credential')) {
      credentials.push(cred);
    }
  }
  
  return credentials;
};

/**
 * Extract Risk Assessment table (5 components)
 * @param {string} content 
 * @returns {Array<{ factor: string, status: string, details: string }>}
 */
export const extractRiskAssessment = (content) => {
  if (!content) return [];
  
  const riskData = [];
  
  // Find Risk Assessment section (with or without emoji)
  let riskStart = content.indexOf('### ⚠️ Risk Assessment');
  if (riskStart === -1) riskStart = content.indexOf('### Risk Assessment');
  if (riskStart === -1) return [];
  
  // Find end of section
  let riskEnd = content.indexOf('###', riskStart + 25);
  if (riskEnd === -1) riskEnd = content.indexOf(':::', riskStart + 25);
  if (riskEnd === -1) riskEnd = content.length;
  
  const riskSection = content.substring(riskStart, riskEnd);
  
  // Parse table rows: | **🚩 Red Flags** | ✅ None Detected | Clean profile |
  const rowPattern = /\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|/g;
  let match;
  
  while ((match = rowPattern.exec(riskSection)) !== null) {
    const factor = match[1].trim();
    const status = match[2].trim();
    const details = match[3].trim();
    
    // Skip header rows
    if (factor.toLowerCase().includes('factor') || status.toLowerCase().includes('status')) continue;
    if (factor.includes('---')) continue;
    
    if (factor && status) {
      riskData.push({ factor, status, details });
    }
  }
  
  return riskData;
};

/**
 * Extract assessment and strengths from conclusion
 * @param {string} content 
 * @returns {{ assessment: string, strengths: string[] }}
 */
export const extractAssessment = (content) => {
  if (!content) return { assessment: null, strengths: [] };
  
  // Find conclusion section
  const conclusionStart = content.indexOf(':::conclusion');
  if (conclusionStart === -1) return { assessment: null, strengths: [] };
  
  const conclusionEnd = content.indexOf(':::', conclusionStart + 13);
  const conclusionContent = conclusionEnd !== -1 
    ? content.substring(conclusionStart + 13, conclusionEnd)
    : content.substring(conclusionStart + 13);
  
  // Extract assessment (text after **Assessment:**)
  const assessmentMatch = conclusionContent.match(/\*\*Assessment:\*\*\s*(.+?)(?=\*\*Key Strengths|$)/s);
  const assessment = assessmentMatch ? assessmentMatch[1].trim() : null;
  
  // Extract strengths
  const strengths = [];
  const strengthsMatch = conclusionContent.match(/\*\*Key Strengths:\*\*([\s\S]*?)$/);
  
  if (strengthsMatch) {
    const bulletPattern = /[-•*]\s*(.+)/g;
    let match;
    while ((match = bulletPattern.exec(strengthsMatch[1])) !== null) {
      const strength = match[1].trim();
      if (strength && !strength.startsWith('[')) {
        strengths.push(strength);
      }
    }
  }
  
  return { assessment, strengths };
};

/**
 * Parse full single candidate response
 * @param {string} content - Raw LLM output
 * @returns {Object} Parsed profile data
 */
export const parseSingleCandidateProfile = (content) => {
  if (!content || !isSingleCandidateResponse(content)) {
    return null;
  }
  
  const candidateInfo = extractCandidateInfo(content);
  const { assessment, strengths } = extractAssessment(content);
  
  // Group skills by category for efficient display
  const rawSkills = extractSkills(content);
  const groupedSkills = groupSkillsByCategory(rawSkills);
  
  return {
    candidateName: candidateInfo?.name || 'Unknown Candidate',
    cvId: candidateInfo?.cvId || '',
    summary: extractSummary(content),
    highlights: extractHighlights(content),
    career: extractCareer(content),
    skills: groupedSkills,
    credentials: extractCredentials(content),
    assessment,
    strengths,
    riskAssessment: extractRiskAssessment(content)
  };
};

/**
 * Group skills by category for efficient display
 * Input: [{ area: 'Design', details: 'X' }, { area: 'Design', details: 'Y' }]
 * Output: [{ area: 'Design', details: 'X, Y' }]
 */
const groupSkillsByCategory = (skills) => {
  if (!skills || skills.length === 0) return [];
  
  const grouped = {};
  
  for (const skill of skills) {
    const area = skill.area;
    if (!grouped[area]) {
      grouped[area] = [];
    }
    grouped[area].push(skill.details);
  }
  
  // Convert to array format with combined details
  return Object.entries(grouped).map(([area, details]) => ({
    area,
    details: details.join(', ')
  }));
};

export default parseSingleCandidateProfile;
