import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { GitPullRequest, ChevronLeft, RotateCcw } from 'lucide-react';
import { pullRequestService } from '../services/pullRequestService';
import { repositoryService } from '../services/repositoryService';
import type { PullRequestRead, RepositoryRead } from '../types';
import { PRCard } from '../components/pullRequest/PRCard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Button } from '../components/common/Button';

export const PullRequestsPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const [prs, setPrs] = useState<PullRequestRead[]>([]);
  const [repository, setRepository] = useState<RepositoryRead | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshTick, setRefreshTick] = useState(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    if (!repoId) return;
    mountedRef.current = true;

    const run = async () => {
      setLoading(true);
      setError('');
      try {
        const [prRes, repoRes] = await Promise.allSettled([
          pullRequestService.getPullRequestsForRepository(repoId, 1, 50),
          repositoryService.getRepositoryById(repoId),
        ]);
        if (!mountedRef.current) return;
        if (prRes.status === 'fulfilled') {
          setPrs(prRes.value.items);
          setTotal(prRes.value.total);
        } else {
          setError(prRes.reason instanceof Error ? prRes.reason.message : 'Failed to load pull requests');
        }
        if (repoRes.status === 'fulfilled') {
          setRepository(repoRes.value);
        }
      } catch (err) {
        if (!mountedRef.current) return;
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    };

    void run();
    return () => { mountedRef.current = false; };
  }, [repoId, refreshTick]);

  const handleRefresh = () => setRefreshTick(t => t + 1);
  const repoName = repository?.full_name || repoId || 'Repository';

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Link to="/repositories" className="hover:text-slate-200 flex items-center gap-1 transition-colors">
          <ChevronLeft className="w-3.5 h-3.5" />
          Repositories
        </Link>
        <span className="text-slate-700">/</span>
        <span className="text-slate-300 font-mono truncate">{repoName}</span>
      </div>

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <GitPullRequest className="w-5 h-5 text-slate-400" />
            <h1 className="text-xl font-bold text-slate-100">Pull Requests</h1>
          </div>
          <p className="text-sm text-slate-400">
            {repository ? (
              <>Pull requests for <code className="text-indigo-400 font-mono text-xs">{repository.full_name}</code></>
            ) : (
              'Pull requests for this repository'
            )}
            {!loading && total > 0 && <span className="ml-1 text-slate-500">({total} total)</span>}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          icon={<RotateCcw className="w-3.5 h-3.5" />}
          onClick={handleRefresh}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      {/* States */}
      {loading && <LoadingState message="Loading pull requests…" />}

      {!loading && error && (
        <ErrorState title="Failed to load pull requests" message={error} onRetry={handleRefresh} />
      )}

      {!loading && !error && prs.length === 0 && (
        <EmptyState
          icon={<GitPullRequest className="w-6 h-6" />}
          title="No pull requests"
          description="There are no pull requests registered for this repository in the SecurePR backend."
        />
      )}

      {!loading && !error && prs.length > 0 && (
        <div className="space-y-2.5">
          {prs.map(pr => (
            <PRCard key={pr.id} pr={pr} />
          ))}
        </div>
      )}
    </div>
  );
};
