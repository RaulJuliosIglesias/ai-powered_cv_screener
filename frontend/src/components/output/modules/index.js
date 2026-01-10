/**
 * Frontend Modules - Reusable UI components for structured output
 * 
 * ARCHITECTURE:
 * - MODULES: Individual reusable components (this folder)
 * - STRUCTURES: Complete views that combine modules (parent folder)
 * 
 * The same module can be used by multiple structures.
 */

// Core display modules
export { default as RiskAssessmentTable } from './RiskAssessmentTable';
export { default as RankingTable } from './RankingTable';
export { default as MatchScoreCard } from './MatchScoreCard';
export { default as TeamCompositionView } from './TeamCompositionView';
export { default as TeamBuildView } from './TeamBuildView';
export { default as VerificationResult } from './VerificationResult';
export { default as PoolSummary } from './PoolSummary';
export { default as SearchResultsTable } from './SearchResultsTable';
export { default as TopPickCard } from './TopPickCard';

// NEW: Enhanced comparison modules
export { default as WinnerCard } from './WinnerCard';
export { default as ComparisonMatrix } from './ComparisonMatrix';

// NEW: Utility modules
export { default as ConfidenceIndicator } from './ConfidenceIndicator';
export { default as QuickActions } from './QuickActions';

// V8: Enhanced source attribution
export { default as SourcesPanel } from '../SourcesPanel';
