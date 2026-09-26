import React, { useState } from 'react';
import { GitCommit, User, Calendar, Hash, ChevronDown, ChevronRight, Loader2, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import type { CommitRead, CommitAnalysisRead } from '../../types';
import { Card, CardContent } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { ErrorState } from '../common/ErrorState';
import { commitService } from '../../services/commitService';
import { cn } from '../../lib/utils';

interface CommitRowProps {
  commit: CommitRead;
}

function getOverallStatusVariant(status: string): 'success' | 'medium' | 'secondary' {
  switch (status.toUpperCase()) {
    case 'NO_SIGNIFICANT_GAPS': return 'success';
    case 'NEEDS_REVIEW': return 'medium';
    case 'INSUFFICIENT_EVIDENCE': return 'secondary';
    default: return 'secondary';
  }
}

function getOverallStatusLabel(status: string): string {
  switch (status.toUpperCase()) {
    case 'NO_SIGNIFICANT_GAPS': return 'No Significant Gaps';
    case 'NEEDS_REVIEW': return 'Needs Review';
    case 'INSUFFICIENT_EVIDENCE': return 'Insufficient Evidence';
    default: return status;
  }
}

const NoteSection: React.FC<{ label: string; content: string | null }> = ({ label, content }) => {
  if (!content) return null;
  return (
    <div className="space-y-1">
      <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">{label}</p>
      <p className="text-xs text-slate-300 leading-relaxed">{content}</p>
    </div>
  );
};

export const CommitRow: React.FC<CommitRowProps> = ({ commit }) => {
  const [expanded, setExpanded] = useState(false);
  const [analysisState, setAnalysisState] = useState<
    'idle' | 'loading' | 'done' | 'error'
  >('idle');
  const [analysis, setAnalysis] = useState<CommitAnalysisRead | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');

  const handleAnalyze = async () => {
    setAnalysisState('loading');
    setErrorMsg('');
    try {
      const result = await commitService.triggerCommitAnalysis(commit.sha);
      setAnalysis(result);
      setAnalysisState('done');
      setExpanded(true);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to trigger commit analysis');
      setAnalysisState('error');
    }
  };

  const firstLine = commit.message.split('\n')[0];
  const hasMoreLines = commit.message.includes('\n');

  return (
    <Card className="transition-all hover:border-slate-700/60">
      {/* Main commit row */}
      <div className="p-4 flex items-start gap-3">
        <div className="shrink-0 w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mt-0.5">
          <GitCommit className="w-3.5 h-3.5 text-slate-400" />
        </div>

        <div className="flex-1 min-w-0">
          <button
            className="text-left w-full"
            onClick={() => setExpanded(!expanded)}
          >
            <p className="text-sm font-medium text-slate-200 leading-snug">{firstLine}</p>
            {hasMoreLines && !expanded && (
              <span className="text-xs text-slate-500 italic">Click to expand full message</span>
            )}
          </button>

          <div className="flex items-center gap-4 mt-2 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs font-mono text-slate-500">
              <Hash className="w-3 h-3" />
              {commit.sha.slice(0, 10)}
            </div>
            {(commit.author_login || commit.author_name) && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <User className="w-3 h-3 text-slate-500" />
                {commit.author_login || commit.author_name}
              </div>
            )}
            {commit.committed_at && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Calendar className="w-3 h-3 text-slate-500" />
                {new Date(commit.committed_at).toLocaleString()}
              </div>
            )}
            {commit.parent_sha && (
              <div className="flex items-center gap-1 text-xs font-mono text-slate-600">
                parent: {commit.parent_sha.slice(0, 8)}
              </div>
            )}
          </div>
        </div>

        {/* Analyze button */}
        <div className="shrink-0 flex items-center gap-2 ml-2">
          {analysisState === 'done' && analysis && (
            <Badge variant={getOverallStatusVariant(analysis.overall_status)} className="text-[10px] py-0">
              {getOverallStatusLabel(analysis.overall_status)}
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            loading={analysisState === 'loading'}
            icon={analysisState === 'done' ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : undefined}
            onClick={handleAnalyze}
            disabled={analysisState === 'loading'}
            className="whitespace-nowrap"
          >
            {analysisState === 'loading' ? 'Analyzing...' : analysisState === 'done' ? 'Re-analyze' : 'Analyze Commit'}
          </Button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Toggle expanded"
          >
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <CardContent className="pt-0 border-t border-slate-800/60">
          <div className="pt-3 space-y-4">
            {/* Full commit message */}
            {hasMoreLines && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-1.5">Full Commit Message</p>
                <pre className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-lg text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {commit.message}
                </pre>
              </div>
            )}

            {/* Analysis loading */}
            {analysisState === 'loading' && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                Running completeness analysis on commit {commit.sha.slice(0, 10)}…
              </div>
            )}

            {/* Analysis error */}
            {analysisState === 'error' && (
              <ErrorState
                title="Commit analysis failed"
                message={errorMsg}
                onRetry={handleAnalyze}
              />
            )}

            {/* Analysis result */}
            {analysisState === 'done' && analysis && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge
                    variant={getOverallStatusVariant(analysis.overall_status)}
                    className="gap-1.5"
                  >
                    {analysis.status.toUpperCase() === 'COMPLETED'
                      ? <CheckCircle className="w-3 h-3" />
                      : <Clock className="w-3 h-3" />
                    }
                    Status: {analysis.status}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    Overall: {getOverallStatusLabel(analysis.overall_status)}
                  </Badge>
                </div>

                <NoteSection label="Summary" content={analysis.summary} />
                <NoteSection label="Implementation Notes" content={analysis.implementation_notes} />
                <NoteSection label="Testing Notes" content={analysis.testing_notes} />
                <NoteSection label="Error Handling" content={analysis.error_handling_notes} />
                <NoteSection label="Documentation" content={analysis.documentation_notes} />
                <NoteSection label="Placeholder Notes" content={analysis.placeholder_notes} />

                {/* Signals */}
                {analysis.signals && Object.keys(analysis.signals).length > 0 && (
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Completeness Signals</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {Object.entries(analysis.signals).map(([key, value]) => (
                        <div
                          key={key}
                          className={cn(
                            'flex items-center gap-2 p-2 rounded-md border text-xs',
                            value === true
                              ? 'bg-emerald-950/20 border-emerald-900/30 text-emerald-300'
                              : value === false
                              ? 'bg-red-950/20 border-red-900/30 text-red-300'
                              : 'bg-slate-900/60 border-slate-800 text-slate-400'
                          )}
                        >
                          {value === true && <CheckCircle className="w-3 h-3 text-emerald-400 shrink-0" />}
                          {value === false && <AlertTriangle className="w-3 h-3 text-red-400 shrink-0" />}
                          <span className="font-mono truncate">{key.replace(/_/g, ' ')}</span>
                          {typeof value !== 'boolean' && (
                            <span className="ml-auto text-[10px] text-slate-400 font-mono">{String(value)}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Idle — no analysis yet */}
            {analysisState === 'idle' && (
              <p className="text-xs text-slate-500 italic">
                Click "Analyze Commit" to run a completeness check on this commit.
              </p>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
};
