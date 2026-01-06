/**
 * QuickActions - Quick action buttons for candidates
 */

import React, { useState } from 'react';
import { FileText, Star, Mail, Share2, Bookmark, Check, Copy } from 'lucide-react';

const QuickActions = ({ candidateName, cvId, onOpenCV, compact = false }) => {
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSave = () => {
    setSaved(!saved);
    // Future: integrate with backend save functionality
  };

  const handleCopyLink = () => {
    const link = `${window.location.origin}/cv/${cvId}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEmail = () => {
    const subject = encodeURIComponent(`Regarding candidate: ${candidateName}`);
    const body = encodeURIComponent(`Hi,\n\nI'd like to discuss the candidate ${candidateName}.\n\nBest regards`);
    window.open(`mailto:?subject=${subject}&body=${body}`);
  };

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        <button
          onClick={() => onOpenCV?.(cvId)}
          className="p-1.5 hover:bg-slate-700/50 rounded transition-colors"
          title="View CV"
        >
          <FileText className="w-3.5 h-3.5 text-blue-400" />
        </button>
        <button
          onClick={handleSave}
          className="p-1.5 hover:bg-slate-700/50 rounded transition-colors"
          title={saved ? "Saved" : "Save"}
        >
          {saved ? (
            <Bookmark className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
          ) : (
            <Bookmark className="w-3.5 h-3.5 text-slate-400" />
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 p-2 bg-slate-800/30 rounded-lg">
      <button
        onClick={() => onOpenCV?.(cvId)}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-colors text-sm"
      >
        <FileText className="w-4 h-4" />
        <span>View CV</span>
      </button>
      
      <button
        onClick={handleSave}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors text-sm ${
          saved 
            ? 'bg-yellow-500/20 text-yellow-400' 
            : 'bg-slate-700/50 hover:bg-slate-700 text-slate-300'
        }`}
      >
        {saved ? (
          <>
            <Bookmark className="w-4 h-4 fill-yellow-400" />
            <span>Saved</span>
          </>
        ) : (
          <>
            <Bookmark className="w-4 h-4" />
            <span>Save</span>
          </>
        )}
      </button>

      <button
        onClick={handleEmail}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors text-sm"
      >
        <Mail className="w-4 h-4" />
        <span>Contact</span>
      </button>

      <button
        onClick={handleCopyLink}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors text-sm"
      >
        {copied ? (
          <>
            <Check className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-400">Copied!</span>
          </>
        ) : (
          <>
            <Copy className="w-4 h-4" />
            <span>Share</span>
          </>
        )}
      </button>
    </div>
  );
};

export default QuickActions;
