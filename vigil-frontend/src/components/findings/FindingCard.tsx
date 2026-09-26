import React, { useState } from 'react';
import { ChevronDown, ChevronRight, MapPin, FileCode, AlertTriangle, Lightbulb, Search, Tag } from 'lucide-react';
import type { FindingRead } from '../../types';
import { Card, CardContent } from '../common/Card';
import { Badge } from '../common/Badge';
import { SeverityBadge } from './SeverityBadge';
import { cn } from '../../lib/utils';

interface FindingCardProps {
  finding: FindingRead;
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    SECURITY: 'Security',
    LOGIC: 'Logic',
    ERROR_HANDLING: 'Error Handling',
    TESTING: 'Testing',
    MAINTAINABILITY: 'Maintainability',
    CODE_QUALITY: 'Code Quality',
    DOCUMENTATION: 'Documentation',
    PERFORMANCE: 'Performance',
  };
  return labels[category.toUpperCase()] || category;
}

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    SEMGREP: 'Semgrep',
    GITLEAKS: 'Gitleaks',
    TRIVY: 'Trivy',
    MS_SECURITY_DEVOPS: 'MS Security DevOps',
    AI_REVIEW: 'SecurePR AI',
  };
  return labels[source.toUpperCase()] || source;
}

function getStatusVariant(status: string): 'outline' | 'critical' | 'success' | 'secondary' {
  switch (status.toUpperCase()) {
    case 'OPEN': return 'critical';
    case 'RESOLVED': return 'success';
    case 'ACKNOWLEDGED': return 'outline';
    case 'FALSE_POSITIVE': return 'secondary';
    default: return 'outline';
  }
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding }) => {
  const [expanded, setExpanded] = useState(false);
  const evidence = finding.evidence;

  return (
    <Card className={cn(
      'transition-all',
      finding.severity.toUpperCase() === 'CRITICAL' && 'border-red-900/40',
      finding.severity.toUpperCase() === 'HIGH' && 'border-orange-900/30',
    )}>
      {/* Header — always visible */}
      <button
        className="w-full text-left p-4 flex items-start gap-3 group hover:bg-slate-800/20 transition-colors rounded-t-xl"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <div className="mt-0.5 shrink-0">
          <SeverityBadge severity={finding.severity} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-slate-100 leading-snug pr-2 text-left">{finding.message}</p>
            <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
              <Badge variant="outline" className="text-[10px] py-0">
                {getCategoryLabel(finding.category)}
              </Badge>
              <Badge variant={getStatusVariant(finding.status)} className="text-[10px] py-0 uppercase">
                {finding.status}
              </Badge>
              {expanded
                ? <ChevronDown className="w-4 h-4 text-slate-500 group-hover:text-slate-300 transition-colors" />
                : <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-slate-300 transition-colors" />
              }
            </div>
          </div>

          {/* Location line — always visible */}
          <div className="flex items-center gap-4 mt-2 flex-wrap">
            {finding.file_path && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                <FileCode className="w-3.5 h-3.5 text-slate-500" />
                <span className="truncate max-w-xs">{finding.file_path}</span>
                {finding.start_line !== null && (
                  <span className="flex items-center gap-0.5 text-slate-500">
                    <MapPin className="w-3 h-3" />
                    L{finding.start_line}
                    {finding.end_line && finding.end_line !== finding.start_line && `–${finding.end_line}`}
                  </span>
                )}
              </div>
            )}
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <Tag className="w-3 h-3" />
              <span>{getSourceLabel(finding.source)}</span>
            </div>
            {finding.rule_id && (
              <span className="text-xs font-mono text-slate-500">{finding.rule_id}</span>
            )}
          </div>
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <CardContent className="pt-0 border-t border-slate-800/60">
          <div className="space-y-3 pt-3">
            {/* Problem */}
            {evidence?.problem && (
              <EvidenceSection
                icon={<AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                label="Problem"
                content={evidence.problem}
              />
            )}

            {/* Why it matters */}
            {evidence?.why && (
              <EvidenceSection
                icon={<Search className="w-3.5 h-3.5 text-indigo-400" />}
                label="Why It Matters"
                content={evidence.why}
              />
            )}

            {/* Evidence / Code snippet */}
            {(evidence?.evidence || evidence?.code_snippet) && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-slate-500 font-medium mb-1.5">Evidence</p>
                <pre className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {evidence.evidence || evidence.code_snippet}
                </pre>
              </div>
            )}

            {/* Suggestion */}
            {evidence?.suggestion && (
              <EvidenceSection
                icon={<Lightbulb className="w-3.5 h-3.5 text-emerald-400" />}
                label="Suggestion"
                content={evidence.suggestion}
                highlight
              />
            )}

            {/* Description fallback */}
            {evidence?.description && !evidence?.problem && (
              <EvidenceSection
                icon={<AlertTriangle className="w-3.5 h-3.5 text-slate-400" />}
                label="Description"
                content={evidence.description}
              />
            )}

            {/* Raw finding message if no evidence breakdown available */}
            {!evidence && (
              <div className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-lg">
                <p className="text-xs text-slate-300 leading-relaxed">{finding.message}</p>
              </div>
            )}

            {/* Fingerprint */}
            <div className="pt-1 flex items-center gap-2 text-[10px] text-slate-600 font-mono border-t border-slate-800/60">
              <span>fingerprint: {finding.fingerprint}</span>
              {finding.raw_artifact_uri && (
                <a
                  href={finding.raw_artifact_uri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-500 hover:underline"
                >
                  View raw artifact
                </a>
              )}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

const EvidenceSection: React.FC<{
  icon: React.ReactNode;
  label: string;
  content: string;
  highlight?: boolean;
}> = ({ icon, label, content, highlight }) => (
  <div className={cn(
    'p-3 rounded-lg border text-xs leading-relaxed',
    highlight
      ? 'bg-emerald-950/20 border-emerald-900/30 text-emerald-200'
      : 'bg-slate-950/40 border-slate-800/60 text-slate-300'
  )}>
    <div className="flex items-center gap-1.5 mb-1.5">
      {icon}
      <span className="text-[11px] uppercase tracking-wider font-semibold opacity-80">{label}</span>
    </div>
    <p>{content}</p>
  </div>
);
