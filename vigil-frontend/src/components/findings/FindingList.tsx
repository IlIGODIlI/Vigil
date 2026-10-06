import React, { useState } from 'react';
import { Filter, Shield } from 'lucide-react';
import type { FindingRead, FindingSeverity } from '../../types';
import { FindingCard } from './FindingCard';
import { EmptyState } from '../common/EmptyState';
import { Badge } from '../common/Badge';
import { cn } from '../../lib/utils';

interface FindingListProps {
  findings: FindingRead[];
}

const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
};

const ALL_SEVERITIES: FindingSeverity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];

function getSeverityFilterVariant(severity: string, active: boolean) {
  if (!active) return 'outline';
  switch (severity) {
    case 'CRITICAL': return 'critical';
    case 'HIGH': return 'high';
    case 'MEDIUM': return 'medium';
    case 'LOW': return 'low';
    case 'INFO': return 'info';
    default: return 'secondary';
  }
}

export const FindingList: React.FC<FindingListProps> = ({ findings }) => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  // Derive unique sources and statuses from real data
  const sources = Array.from(new Set(findings.map(f => f.source)));
  const statuses = Array.from(new Set(findings.map(f => f.status)));

  // Severity counts
  const severityCounts = findings.reduce<Record<string, number>>((acc, f) => {
    const s = f.severity.toUpperCase();
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  const filtered = findings
    .filter(f => selectedSeverity === 'ALL' || f.severity.toUpperCase() === selectedSeverity)
    .filter(f => selectedSource === 'ALL' || f.source.toUpperCase() === selectedSource)
    .filter(f => selectedStatus === 'ALL' || f.status.toUpperCase() === selectedStatus)
    .sort((a, b) => {
      const aOrder = SEVERITY_ORDER[a.severity.toUpperCase()] ?? 99;
      const bOrder = SEVERITY_ORDER[b.severity.toUpperCase()] ?? 99;
      return aOrder - bOrder;
    });

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-2 p-3 bg-slate-900/60 border border-slate-800 rounded-lg flex-wrap">
        <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium mr-1">
          <Shield className="w-3.5 h-3.5 text-slate-500" />
          {findings.length} finding{findings.length !== 1 ? 's' : ''}
        </span>
        {ALL_SEVERITIES.map(s => {
          const count = severityCounts[s] || 0;
          if (count === 0) return null;
          return (
            <button
              key={s}
              onClick={() => setSelectedSeverity(selectedSeverity === s ? 'ALL' : s)}
              className="cursor-pointer"
            >
              <Badge
                variant={getSeverityFilterVariant(s, selectedSeverity === s) as 'critical' | 'high' | 'medium' | 'low' | 'info' | 'outline'}
                className={cn('text-[10px] py-0.5 transition-all', selectedSeverity === s && 'ring-1 ring-current ring-offset-1 ring-offset-slate-900')}
              >
                {count} {s}
              </Badge>
            </button>
          );
        })}
      </div>

      {/* Filters row */}
      {(sources.length > 1 || statuses.length > 1) && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500 flex items-center gap-1">
            <Filter className="w-3 h-3" />
            Filter:
          </span>

          {sources.length > 1 && (
            <div className="flex items-center gap-1.5">
              {['ALL', ...sources].map(source => (
                <button
                  key={source}
                  onClick={() => setSelectedSource(source)}
                  className={cn(
                    'text-[11px] px-2.5 py-1 rounded-md border transition-colors font-medium',
                    selectedSource === source
                      ? 'bg-slate-700 text-slate-200 border-slate-600'
                      : 'bg-transparent text-slate-500 border-slate-800 hover:border-slate-700 hover:text-slate-300'
                  )}
                >
                  {source === 'ALL' ? 'All Sources' : source}
                </button>
              ))}
            </div>
          )}

          {statuses.length > 1 && (
            <div className="flex items-center gap-1.5 ml-1">
              {['ALL', ...statuses].map(status => (
                <button
                  key={status}
                  onClick={() => setSelectedStatus(status)}
                  className={cn(
                    'text-[11px] px-2.5 py-1 rounded-md border transition-colors font-medium',
                    selectedStatus === status
                      ? 'bg-slate-700 text-slate-200 border-slate-600'
                      : 'bg-transparent text-slate-500 border-slate-800 hover:border-slate-700 hover:text-slate-300'
                  )}
                >
                  {status === 'ALL' ? 'All Statuses' : status}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Findings list */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={<Shield className="w-6 h-6" />}
          title="No findings match the current filters"
          description='Try clearing filters, or no findings were returned for this review.'
        />
      ) : (
        <div className="space-y-2.5">
          {filtered.map(finding => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
};
