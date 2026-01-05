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
  ];
  
  const matchCount = singleCandidateIndicators.filter(pattern => pattern.test(content)).length;
  return matchCount >= 2;
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
  
  return summaryLines.length > 0 ? summaryLines.join(' ') : null;
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
  
  const afterHighlights = content.substring(highlightsStart);
  
  // Find the table rows
  // Pattern: | **emoji Category** | Value |
  const rowPattern = /\|\s*\*\*([^|]+)\*\*\s*\|\s*([^|]+)\|/g;
  let match;
  
  while ((match = rowPattern.exec(afterHighlights)) !== null) {
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
    
    if (category && value && value !== '[' && !value.startsWith('[')) {
      highlights.push({ category, value });
    }
  }
  
  return highlights;
};

/**
 * Extract career trajectory
 * @param {string} content 
 * @returns {Array<{ title: string, company: string, period: string, achievement: string }>}
 */
export const extractCareer = (content) => {
  if (!content) return [];
  
  const career = [];
  
  // Find career section
  const careerStart = content.indexOf('### 💼 Career Trajectory');
  if (careerStart === -1) return [];
  
  // Find end of career section (next ### or ---)
  let careerEnd = content.indexOf('###', careerStart + 1);
  if (careerEnd === -1) careerEnd = content.length;
  
  const careerSection = content.substring(careerStart, careerEnd);
  
  // Pattern: **Title** — *Company* (Year-Year)
  // → Achievement
  const jobPattern = /\*\*([^*]+)\*\*\s*[—–-]\s*\*([^*]+)\*\s*(?:\(([^)]+)\))?/g;
  const achievementPattern = /[→>]\s*(.+)/;
  
  const lines = careerSection.split('\n');
  let currentJob = null;
  
  for (const line of lines) {
    const jobMatch = line.match(/\*\*([^*]+)\*\*\s*[—–-]\s*\*([^*]+)\*\s*(?:\(([^)]+)\))?/);
    
    if (jobMatch) {
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
      const achieveMatch = line.match(achievementPattern);
      if (achieveMatch) {
        currentJob.achievement = achieveMatch[1].trim();
      }
    }
  }
  
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
  
  return {
    candidateName: candidateInfo?.name || 'Unknown Candidate',
    cvId: candidateInfo?.cvId || '',
    summary: extractSummary(content),
    highlights: extractHighlights(content),
    career: extractCareer(content),
    skills: extractSkills(content),
    credentials: extractCredentials(content),
    assessment,
    strengths
  };
};

export default parseSingleCandidateProfile;
