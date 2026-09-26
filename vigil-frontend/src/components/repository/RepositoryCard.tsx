import React from 'react';
import { Link } from 'react-router-dom';
import {
  GitBranch, Lock, Globe, ExternalLink, ArrowRight,
  ShieldAlert, ShieldCheck, GitPullRequest, Clock,
  Code2, Star
} from 'lucide-react';
import type { RepositoryRead } from '../../types';
import { Card, CardContent } from '../common/Card';
import { cn } from '../../lib/utils';
import {
  getDisplayMeta,
  getRiskBgBorder,
  getScoreColor,
  getScoreBarColor,
  type RepoDisplayMeta,
} from '../../data/repoDisplayMeta';

export interface RepositoryCardProps {
  repository: RepositoryRead;
}

const RiskLabel: React.FC<{ risk: RepoDisplayMeta['riskLevel'] }> = ({ risk }) => {
  const styles = getRiskBgBorder(risk);
  const label = {
    critical: 'Critical Risk',
    high: 'High Risk',
    medium: 'Medium Risk',
    low: 'Low Risk',
    clean: 'Clean',
  }[risk];
  const Icon = risk === 'clean' ? ShieldCheck : ShieldAlert;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border', styles)}>
      <Icon className="w-2.5 h-2.5" />
      {label}
    </span>
  );
};

export const RepositoryCard: React.FC<RepositoryCardProps> = ({ repository }) => {
  const meta = getDisplayMeta(repository.name);
  const scoreColor = getScoreColor(meta.securityScore);
  const barColor = getScoreBarColor(meta.securityScore);

  return (
    <Link to={`/repositories/${repository.id}`} className="block group">
      <Card className={cn(
        'hover:border-slate-700/80 transition-all h-full',
        meta.riskLevel === 'critical' && 'border-red-900/30 hover:border-red-800/50',
        meta.riskLevel === 'high' && 'border-orange-900/20 hover:border-orange-800/40',
      )}>
        <CardContent className="p-5 flex flex-col h-full gap-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-[11px] text-slate-500 font-mono truncate">{repository.owner_login}</span>
                <span className="text-slate-700">/</span>
                <h4 className="text-sm font-bold text-slate-100 group-hover:text-indigo-400 transition-colors truncate">
                  {repository.name}
                </h4>
              </div>
              {meta.description && (
                <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2 mt-1">
                  {meta.description}
                </p>
              )}
            </div>
            <div className="shrink-0 flex flex-col items-end gap-1.5">
              <RiskLabel risk={meta.riskLevel} />
              {repository.private ? (
                <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 font-medium">
                  <Lock className="w-2.5 h-2.5" /> Private
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 font-medium">
                  <Globe className="w-2.5 h-2.5" /> Public
                </span>
              )}
            </div>
          </div>

          {/* Security Score Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-medium uppercase tracking-wide">Security Score</span>
              <span className={cn('text-sm font-bold tabular-nums', scoreColor)}>
                {meta.securityScore}<span className="text-[10px] text-slate-600 font-normal">/100</span>
              </span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', barColor)}
                style={{ width: `${meta.securityScore}%` }}
              />
            </div>
          </div>

          {/* Findings summary */}
          <div className="grid grid-cols-4 gap-2">
            <FindingCell count={meta.criticalFindings} label="Critical" colorClass="text-red-400" dotClass="bg-red-500" />
            <FindingCell count={meta.highFindings} label="High" colorClass="text-orange-400" dotClass="bg-orange-500" />
            <FindingCell count={meta.mediumFindings} label="Medium" colorClass="text-amber-400" dotClass="bg-amber-500" />
            <FindingCell count={meta.lowFindings} label="Low" colorClass="text-blue-400" dotClass="bg-blue-500" />
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
            {/* Language */}
            <span className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: meta.languageColor }}
              />
              <Code2 className="w-3 h-3" />
              {meta.language}
            </span>
            {/* Branch */}
            <span className="flex items-center gap-1 font-mono">
              <GitBranch className="w-3 h-3 text-slate-600" />
              {repository.default_branch}
            </span>
            {/* Open PRs */}
            <span className="flex items-center gap-1">
              <GitPullRequest className="w-3 h-3 text-slate-600" />
              <span className={meta.openPRs > 0 ? 'text-indigo-400 font-medium' : ''}>
                {meta.openPRs} PR{meta.openPRs !== 1 ? 's' : ''}
              </span>
            </span>
            {/* Last analyzed */}
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-600" />
              {meta.lastAnalyzed}
            </span>
            {/* Stars */}
            {meta.stars > 0 && (
              <span className="flex items-center gap-1">
                <Star className="w-3 h-3 text-slate-600" />
                {meta.stars}
              </span>
            )}
          </div>

          {/* Topics */}
          {meta.topics.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {meta.topics.map(t => (
                <span key={t} className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300/80 border border-indigo-500/15 font-mono">
                  {t}
                </span>
              ))}
            </div>
          )}

          {/* Footer actions */}
          <div className="mt-auto pt-3 border-t border-slate-800/80 flex items-center justify-between">
            {repository.html_url ? (
              <a
                href={repository.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="w-3 h-3" />
                GitHub
              </a>
            ) : (
              <span className="text-[11px] text-slate-600 flex items-center gap-1">
                <ExternalLink className="w-3 h-3" />
                No URL
              </span>
            )}

            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 group-hover:text-indigo-300 group-hover:translate-x-0.5 transition-all">
              Open Repository
              <ArrowRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};

const FindingCell: React.FC<{
  count: number;
  label: string;
  colorClass: string;
  dotClass: string;
}> = ({ count, label, colorClass, dotClass }) => (
  <div className={cn(
    'flex flex-col items-center p-2 rounded-lg border',
    count > 0
      ? 'bg-slate-900/60 border-slate-800/80'
      : 'bg-slate-950/40 border-slate-900 opacity-50'
  )}>
    <div className="flex items-center gap-1 mb-0.5">
      {count > 0 && <span className={cn('w-1.5 h-1.5 rounded-full', dotClass)} />}
      <span className={cn('text-sm font-bold tabular-nums', count > 0 ? colorClass : 'text-slate-600')}>
        {count}
      </span>
    </div>
    <span className="text-[9px] text-slate-500 font-medium uppercase tracking-wide">{label}</span>
  </div>
);
