import { memo } from 'react';

export const SessionSkeleton = memo(() => (
  <div className="space-y-2 px-2">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg">
        <div className="w-4 h-4 skeleton rounded" />
        <div className="flex-1 space-y-1">
          <div className="h-4 skeleton rounded w-3/4" />
          <div className="h-3 skeleton rounded w-1/4" />
        </div>
      </div>
    ))}
  </div>
));

SessionSkeleton.displayName = 'SessionSkeleton';

export const MessageSkeleton = memo(() => (
  <div className="flex gap-4 max-w-4xl">
    <div className="w-9 h-9 skeleton rounded-full flex-shrink-0" />
    <div className="flex-1 space-y-2">
      <div className="h-4 skeleton rounded w-1/4" />
      <div className="p-4 rounded-2xl bg-slate-100 dark:bg-slate-800 space-y-3">
        <div className="h-4 skeleton rounded w-full" />
        <div className="h-4 skeleton rounded w-5/6" />
        <div className="h-4 skeleton rounded w-4/6" />
        <div className="h-4 skeleton rounded w-3/4" />
      </div>
    </div>
  </div>
));

MessageSkeleton.displayName = 'MessageSkeleton';

export const CVCardSkeleton = memo(() => (
  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 skeleton rounded-lg" />
      <div className="flex-1 space-y-2">
        <div className="h-4 skeleton rounded w-3/4" />
        <div className="h-3 skeleton rounded w-1/2" />
      </div>
    </div>
  </div>
));

CVCardSkeleton.displayName = 'CVCardSkeleton';

export const MetricsSkeleton = memo(() => (
  <div className="space-y-3 p-4">
    <div className="grid grid-cols-4 gap-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="text-center space-y-2">
          <div className="h-8 skeleton rounded w-16 mx-auto" />
          <div className="h-3 skeleton rounded w-12 mx-auto" />
        </div>
      ))}
    </div>
    <div className="space-y-2">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-16 skeleton rounded-lg" />
      ))}
    </div>
  </div>
));

MetricsSkeleton.displayName = 'MetricsSkeleton';

export const TableSkeleton = memo(({ rows = 5, cols = 4 }) => (
  <div className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
    <div className="bg-slate-100 dark:bg-slate-800 p-3 flex gap-4">
      {[...Array(cols)].map((_, i) => (
        <div key={i} className="h-4 skeleton rounded flex-1" />
      ))}
    </div>
    <div className="divide-y divide-slate-200 dark:divide-slate-700">
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="p-3 flex gap-4">
          {[...Array(cols)].map((_, j) => (
            <div key={j} className="h-4 skeleton rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  </div>
));

TableSkeleton.displayName = 'TableSkeleton';

export default {
  SessionSkeleton,
  MessageSkeleton,
  CVCardSkeleton,
  MetricsSkeleton,
  TableSkeleton,
};
