import React from 'react';
import { Link } from 'react-router-dom';
import { GitPullRequest, GitBranch, User, Circle, ArrowRight, Clock } from 'lucide-react';
import type { PullRequestRead } from '../../types';
import { Card, CardContent } from '../common/Card';
import { Badge } from '../common/Badge';
import { cn } from '../../lib/utils';

interface PRCardProps {
  pr: PullRequestRead;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffMins = Math.floor(diffMs / 60000);
  if (diffDays > 30) return date.toLocaleDateString();
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMins > 0) return `${diffMins}m ago`;
  return 'just now';
}

function getPRStatusVariant(status: string): 'success' | 'secondary' | 'outline' | 'info' {
  switch (status.toUpperCase()) {
    case 'OPEN':
      return 'success';
    case 'MERGED':
      return 'info';
    case 'CLOSED':
      return 'secondary';
    default:
      return 'outline';
  }
}

export const PRCard: React.FC<PRCardProps> = ({ pr }) => {
  const statusVariant = getPRStatusVariant(pr.status);

  return (
    <Link to={`/pull-requests/${pr.id}`}>
      <Card className="hover:border-slate-700/80 hover:shadow-indigo-950/20 group transition-all cursor-pointer">
        <CardContent className="p-5">
          <div className="flex items-start gap-4">
            {/* PR Icon */}
            <div className={cn(
              'mt-0.5 shrink-0 w-8 h-8 rounded-lg flex items-center justify-center border',
              pr.status.toUpperCase() === 'OPEN'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : pr.status.toUpperCase() === 'MERGED'
                ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
                : 'bg-slate-800 border-slate-700 text-slate-500'
            )}>
              <GitPullRequest className="w-4 h-4" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono text-slate-500">#{pr.pr_number}</span>
                    <h4 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-400 transition-colors leading-snug truncate">
                      {pr.title}
                    </h4>
                  </div>

                  {/* Branch info */}
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <div className="flex items-center gap-1 text-xs text-slate-400 font-mono bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50">
                      <GitBranch className="w-3 h-3 text-slate-500" />
                      {pr.source_branch}
                    </div>
                    <span className="text-slate-600 text-xs">→</span>
                    <div className="flex items-center gap-1 text-xs text-slate-400 font-mono bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50">
                      {pr.target_branch}
                    </div>
                  </div>

                  {/* Meta row */}
                  <div className="flex items-center gap-4 mt-2.5 flex-wrap">
                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                      <User className="w-3 h-3 text-slate-500" />
                      <span>{pr.author_login}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{formatRelativeTime(pr.updated_at)}</span>
                    </div>
                    {pr.merged_at && (
                      <div className="text-xs text-indigo-400 font-mono">
                        Merged {formatRelativeTime(pr.merged_at)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right-side: status + arrow */}
                <div className="flex items-center gap-3 shrink-0 mt-0.5">
                  <Badge variant={statusVariant} className="gap-1 uppercase tracking-wide">
                    <Circle className="w-1.5 h-1.5 fill-current" />
                    {pr.status}
                  </Badge>
                  <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};
