/**
 * Preprocess message content to handle special blocks and CV links
 * This is a memoizable pure function for performance optimization
 */
export const preprocessContent = (content) => {
  if (!content) return { mainContent: content || '', conclusionContent: null, thinkingContent: null };
  
  let text = content;
  let thinkingContent = null;
  let conclusionContent = null;
  
  // Extract thinking block - try with closing ::: first, then without
  const thinkingMatch = text.match(/:::thinking\s*\n?([\s\S]*?):::/);
  if (thinkingMatch) {
    thinkingContent = thinkingMatch[1].trim();
    text = text.replace(thinkingMatch[0], '');
  }
  
  // Extract conclusion block - multiple patterns
  // Pattern 1: :::conclusion ... ::: (with closing)
  let conclusionMatch = text.match(/:::conclusion\s*\n?([\s\S]*?):::/);
  if (conclusionMatch) {
    conclusionContent = conclusionMatch[1].trim();
    text = text.replace(conclusionMatch[0], '');
  } else {
    // Pattern 2: :::conclusion at start of line followed by content (no closing)
    conclusionMatch = text.match(/:::conclusion\s+(.+)$/m);
    if (conclusionMatch) {
      conclusionContent = conclusionMatch[1].trim();
      text = text.replace(conclusionMatch[0], '');
    }
  }
  
  // Also remove any remaining :::conclusion text that wasn't matched
  text = text.replace(/:::conclusion\s*/g, '');
  
  // Convert various CV reference formats to: Name + icon link (no emoji, just link that renders as button)
  // Format 1: [CV:cv_id] -> link only (renders as FileText icon button)
  text = text.replace(/\[CV:(cv_[a-z0-9_-]+)\]/gi, '[$1]($1)');
  
  // Format 2: **[Name](cv:cv_id)** -> **Name** + icon link
  text = text.replace(/\*\*\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)');
  
  // Format 3: [Name](cv:cv_id) -> Name + icon link
  text = text.replace(/\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)');
  
  // Format 4: **[Name](cv_id)** direct link -> **Name** + icon link
  text = text.replace(/\*\*\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)');
  
  // Format 5: [Name](cv_id) direct link -> Name + icon link (CRITICAL - prevents name as link)
  text = text.replace(/\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)');
  
  // Format 6: (cv:cv_id) standalone -> icon link
  text = text.replace(/\(cv:(cv_[a-z0-9_-]+)\)/gi, ' [$1]($1)');
  
  // Clean up multiple newlines
  text = text.replace(/\n{3,}/g, '\n\n').trim();
  
  return { 
    mainContent: text, 
    conclusionContent,
    thinkingContent 
  };
};

/**
 * Process conclusion content to convert CV references to clickable links
 */
export const processCVReferences = (content) => {
  if (!content) return content;
  
  return content
    .replace(/\*\*\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)')
    .replace(/\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)')
    .replace(/\*\*\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)')
    .replace(/\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)')
    .replace(/\[CV:(cv_[a-z0-9_-]+)\]/gi, '[$1]($1)')
    .replace(/\(cv:(cv_[a-z0-9_-]+)\)/gi, ' [$1]($1)');
};

/**
 * Parse CV filename into components
 */
export const parseCVFilename = (filename) => {
  const name = filename.replace('.pdf', '').replace('.PDF', '');
  const parts = name.split('_');
  
  if (parts.length >= 3) {
    const fileId = parts[0];
    const role = parts[parts.length - 1].replace(/-/g, ' ');
    const candidateName = parts.slice(1, -1).join(' ');
    return { fileId, candidateName, role };
  } else if (parts.length === 2) {
    return { fileId: parts[0], candidateName: parts[1], role: '' };
  }
  return { fileId: '', candidateName: name, role: '' };
};

export default {
  preprocessContent,
  processCVReferences,
  parseCVFilename,
};
