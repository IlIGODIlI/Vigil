import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { GitPullRequest, GitCommitHorizontal, MessageSquare, FileCode, ShieldAlert, CheckCircle, XCircle, Clock, Plus, Minus } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { OrbSM, OrbXS } from '../components/AIOrb';

const PRS = [
  {
    id: 47, title: 'feat: add user authentication via JWT', repo: 'api-gateway',
    author: 'Priya Sharma', branch: 'feat/jwt-auth', base: 'main',
    severity: 'critical', findings: 2, files: 8, additions: 234, deletions: 12,
    aiStatus: 'complete', humanStatus: 'pending', time: '2h ago', comments: 3,
    description: 'Implements JWT-based authentication. Adds token generation, validation middleware, and refresh token support.',
    findings_data: [
      { severity: 'critical', title: 'Hardcoded JWT signing secret', file: 'src/auth/jwt.go', line: 42, desc: 'A JWT signing secret is hardcoded as a string literal. An attacker with source access can forge any token.', impact: 'Source or history access would allow an attacker to forge valid user tokens.', fix: 'Use os.Getenv("JWT_SECRET") and rotate the current value immediately.' },
      { severity: 'high', title: 'Missing token expiry validation', file: 'src/middleware/auth.go', line: 78, desc: 'Tokens are validated for signature integrity but the exp claim is not checked. Stolen tokens remain permanently valid.', impact: 'Compromised sessions cannot be reliably expired or revoked.', fix: 'Add jwt.WithExpirationRequired() or explicitly check the exp claim.' },
    ],
  },
  {
    id: 51, title: 'fix: update axios dependency to 1.6.2', repo: 'web-frontend',
    author: 'Rohan Mehta', branch: 'fix/axios-update', base: 'main',
    severity: 'medium', findings: 1, files: 2, additions: 5, deletions: 3,
    aiStatus: 'complete', humanStatus: 'pending', time: '4h ago', comments: 1,
    description: 'Updates axios from 1.4.0 to 1.6.2 to patch CVE-2023-45857.',
    findings_data: [
      { severity: 'medium', title: 'Vulnerable axios version (CVE-2023-45857)', file: 'package.json', line: 18, desc: 'The current axios version leaks CSRF tokens across origins under certain configurations.', impact: 'Sensitive request headers could be disclosed to an untrusted origin.', fix: 'This PR addresses the issue. Approve after confirming the lock file update.' },
    ],
  },
  {
    id: 52, title: 'fix: restrict production CORS origins', repo: 'auth-service',
    author: 'Anita Bose', branch: 'fix/cors-origins', base: 'main',
    severity: 'low', findings: 1, files: 2, additions: 8, deletions: 3,
    aiStatus: 'complete', humanStatus: 'pending', time: '1d ago', comments: 1,
    description: 'Restricts production CORS configuration to approved application origins.',
    findings_data: [
      { severity: 'low', title: 'Overly broad CORS configuration', file: 'src/server/config.go', line: 23, desc: 'CORS currently allows all origins and should be restricted before production exposure.', impact: 'Untrusted origins could interact with endpoints that rely on browser origin controls.', fix: 'Replace the wildcard with an explicit list of approved production origins.' },
    ],
  },
  {
    id: 53, title: 'fix: sanitize search endpoint input', repo: 'api-gateway',
    author: 'Priya Sharma', branch: 'fix/search-input', base: 'main',
    severity: 'info', findings: 0, files: 2, additions: 12, deletions: 3,
    aiStatus: 'complete', humanStatus: 'pending', time: '1h ago', comments: 1,
    description: 'Updates search input handling and request-length validation.',
    findings_data: [],
  },
  {
    id: 54, title: 'feat: add rate limiting to auth routes', repo: 'auth-service',
    author: 'Anita Bose', branch: 'feat/auth-rate-limit', base: 'main',
    severity: 'info', findings: 0, files: 3, additions: 34, deletions: 2,
    aiStatus: 'complete', humanStatus: 'pending', time: '5h ago', comments: 2,
    description: 'Adds rate-limit middleware to authentication routes.',
    findings_data: [],
  },
  {
    id: 43, title: 'refactor: extract auth middleware', repo: 'auth-service',
    author: 'Anita Bose', branch: 'refactor/auth-middleware', base: 'main',
    severity: 'low', findings: 0, files: 6, additions: 89, deletions: 112,
    aiStatus: 'analyzing', humanStatus: 'pending', time: '6h ago', comments: 0,
    description: 'Extracts authentication middleware into a separate module for reusability.',
    findings_data: [],
  },
  {
    id: 39, title: 'chore: update CI pipeline config', repo: 'infrastructure',
    author: 'Dev Kapoor', branch: 'chore/ci-update', base: 'main',
    severity: 'info', findings: 0, files: 3, additions: 24, deletions: 18,
    aiStatus: 'complete', humanStatus: 'approved', time: '1d ago', comments: 2,
    description: 'Updates GitHub Actions to use Node 20 and a faster cache strategy.',
    findings_data: [],
  },
];

type PR = typeof PRS[0];
type AnalysisState = 'idle' | 'analyzing' | 'complete' | 'failed';

function SevBadge({ s }: { s: string }) {
  const cls = `sev sev-${s === 'medium' ? 'medium' : s}`;
  const labels: Record<string, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low', info: 'No findings' };
  return <span className={cls}>{labels[s] ?? s}</span>;
}

function findingsSummary(pr: PR, analysisState: AnalysisState = pr.aiStatus === 'analyzing' ? 'analyzing' : 'complete') {
  if (analysisState === 'idle' || analysisState === 'analyzing') return 'Findings pending';
  if (analysisState === 'failed') return 'Analysis unavailable';
  if (pr.findings_data.length === 0) return 'No security findings';

  const order = ['critical', 'high', 'medium', 'low'] as const;
  return order
    .map(severity => ({
      severity,
      count: pr.findings_data.filter(finding => finding.severity === severity).length,
    }))
    .filter(item => item.count > 0)
    .map(item => `${item.count} ${item.severity.charAt(0).toUpperCase()}${item.severity.slice(1)}`)
    .join(' · ');
}

function PRListItem({ pr, active, onClick }: { pr: PR; active: boolean; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: '12px 14px',
        borderRadius: 5,
        border: `1px solid ${active ? 'color-mix(in srgb, var(--primary) 28%, var(--border))' : 'var(--border)'}`,
        borderLeft: `2px solid ${active ? 'var(--primary)' : 'transparent'}`,
        background: active ? 'var(--secondary)' : 'var(--card)',
        boxShadow: active ? 'var(--shadow-sm)' : 'none',
        cursor: 'pointer',
        transition: 'all 140ms',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>#{pr.id}</span>
        <SevBadge s={pr.severity} />
        {pr.humanStatus === 'approved' && <CheckCircle size={11} style={{ color: 'var(--status-safe)', marginLeft: 'auto' }} />}
        {pr.humanStatus === 'pending' && pr.aiStatus === 'complete' && <Clock size={11} style={{ color: 'var(--status-warn)', marginLeft: 'auto' }} />}
        {pr.aiStatus === 'analyzing' && (
          <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', color: 'var(--ai)' }}>
            <span className="dot dot-pulse" style={{ width: 5, height: 5, background: 'var(--ai)' }} />
            AI
          </span>
        )}
      </div>
      <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--foreground)', marginBottom: 3, lineHeight: 1.3, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
        {pr.title}
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)', marginBottom: 4 }}>
        {pr.repo} · {pr.author} · {pr.time}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '3px 8px', fontSize: '0.72rem' }}>
        <span style={{ color: pr.aiStatus === 'complete' ? 'var(--status-safe)' : 'var(--ai)' }}>
          {pr.aiStatus === 'complete' ? 'AI analysis complete' : 'AI analyzing'}
        </span>
        <span style={{ color: pr.findings > 0 ? 'var(--status-critical)' : 'var(--muted-foreground)' }}>
          {pr.humanStatus === 'pending' && pr.aiStatus === 'complete'
            ? `Human review pending · ${pr.findings} finding${pr.findings === 1 ? '' : 's'}`
            : pr.humanStatus === 'approved'
              ? `Reviewed · ${pr.findings} finding${pr.findings === 1 ? '' : 's'}`
              : 'Findings pending'}
        </span>
      </div>
    </div>
  );
}

function PRDetail({ pr }: { pr: PR }) {
  const [tab, setTab] = useState<'overview' | 'findings' | 'files' | 'commits'>('overview');
  const [decision, setDecision] = useState(pr.humanStatus);
  const [analysisState, setAnalysisState] = useState<AnalysisState>(
    pr.aiStatus === 'analyzing' ? 'analyzing' : 'complete',
  );

  useEffect(() => {
    setTab('overview');
    setDecision(pr.humanStatus);
    setAnalysisState(pr.aiStatus === 'analyzing' ? 'analyzing' : 'complete');
  }, [pr.id, pr.aiStatus, pr.humanStatus]);

  const runAnalysis = () => {
    setAnalysisState('analyzing');
    window.setTimeout(() => setAnalysisState(navigator.onLine ? 'complete' : 'failed'), 1800);
  };

  const aiStatus = analysisState === 'analyzing';
  const aiBg = aiStatus
    ? 'color-mix(in srgb, var(--ai) 6%, var(--card))'
    : pr.findings > 0
    ? 'color-mix(in srgb, var(--status-critical) 5%, var(--card))'
    : 'color-mix(in srgb, var(--status-safe) 5%, var(--card))';
  const aiBorder = aiStatus
    ? 'color-mix(in srgb, var(--ai) 18%, var(--border))'
    : pr.findings > 0
    ? 'color-mix(in srgb, var(--status-critical) 18%, var(--border))'
    : 'color-mix(in srgb, var(--status-safe) 18%, var(--border))';

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden', height: 'fit-content' }}>
      {/* PR header */}
      <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <SevBadge s={pr.severity} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>
            {pr.repo}#{pr.id}
          </span>
          <span style={{ fontSize: '0.7rem', color: 'var(--muted-foreground)' }}>
            {pr.author} · {pr.time}
          </span>
          <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: decision === 'approved' ? 'var(--status-safe)' : decision === 'pending' ? 'var(--status-warn)' : 'var(--status-critical)' }}>
            {decision === 'approved' ? 'Approved' : decision === 'rejected' ? 'Changes requested' : 'Human review pending'}
          </span>
        </div>
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--foreground)', margin: '0 0 8px', lineHeight: 1.3 }}>
          {pr.title}
        </h2>
        <p style={{ fontSize: '0.78rem', color: 'var(--secondary-foreground)', lineHeight: 1.65, margin: '0 0 12px' }}>
          {pr.description}
        </p>
        <div style={{ display: 'flex', gap: 14, fontSize: '0.72rem', color: 'var(--muted-foreground)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <FileCode size={11} /> {pr.files} files
          </span>
          <span style={{ color: 'var(--status-safe)', display: 'flex', alignItems: 'center', gap: 3 }}>
            <Plus size={10} /> {pr.additions}
          </span>
          <span style={{ color: 'var(--status-critical)', display: 'flex', alignItems: 'center', gap: 3 }}>
            <Minus size={10} /> {pr.deletions}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <MessageSquare size={11} /> {pr.comments}
          </span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem' }}>
            {pr.branch} → {pr.base}
          </span>
        </div>
      </div>

      {/* AI analysis banner */}
      <div className="pr-ai-review-banner" style={{ padding: '10px 20px', background: aiBg, borderBottom: `1px solid ${aiBorder}`, display: 'flex', alignItems: 'center', gap: 10 }}>
        {aiStatus ? (
          <OrbSM variant="active" />
        ) : (
          <OrbXS size={14} variant="active" />
        )}
        <span style={{ fontSize: '0.78rem', color: 'var(--foreground)', flex: 1 }}>
          {analysisState === 'idle'
            ? 'Vigil is ready to analyze this pull request.'
            : aiStatus
            ? 'AI security analysis in progress…'
            : analysisState === 'failed'
            ? 'Analysis failed. No results were changed.'
            : pr.findings > 0
            ? `AI found ${pr.findings} security finding${pr.findings > 1 ? 's' : ''} — human review required`
            : 'AI analysis complete — no security findings'}
        </span>
        {analysisState === 'idle' && (
          <button className="btn btn-primary btn-sm" onClick={runAnalysis}>Run analysis</button>
        )}
        {analysisState === 'analyzing' && (
          <div style={{ width: 72, height: 2, overflow: 'hidden', background: 'var(--secondary)', borderRadius: 1 }}>
            <div style={{ width: '65%', height: '100%', background: 'var(--ai)', animation: 'analysis-progress 1.2s ease-in-out infinite' }} />
          </div>
        )}
        {analysisState === 'failed' && (
          <button className="btn btn-secondary btn-sm" onClick={runAnalysis}>Retry</button>
        )}
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ padding: '0 4px' }}>
        {(['overview', 'findings', 'files', 'commits'] as const).map(t => (
          <button
            key={t}
            className={`tab${tab === t ? ' active' : ''}${t === 'findings' && pr.findings > 0 ? ' pr-findings-tab' : ''}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
            {t === 'findings' && pr.findings > 0 && (
              <span style={{ marginLeft: 5, fontSize: '0.7rem', fontWeight: 700, background: 'var(--status-critical)', color: '#fff', borderRadius: 10, padding: '0 5px' }}>
                {pr.findings}
              </span>
            )}
          </button>
        ))}
      </div>

      <div style={{ padding: '18px 20px' }}>
        {/* Overview tab */}
        {tab === 'overview' && (
          <div>
            <div className="stage3-summary-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
              {[
                ['AI Analysis', analysisState === 'complete' ? 'Complete' : analysisState === 'analyzing' ? 'In progress' : analysisState === 'failed' ? 'Failed' : 'Ready', analysisState === 'complete' ? 'var(--status-safe)' : analysisState === 'failed' ? 'var(--status-critical)' : 'var(--ai)'],
                ['Human Review', decision === 'approved' ? 'Approved' : decision === 'rejected' ? 'Changes requested' : 'Pending', decision === 'approved' ? 'var(--status-safe)' : decision === 'pending' ? 'var(--muted-foreground)' : 'var(--status-critical)'],
                ['Files changed', String(pr.files), 'var(--foreground)'],
                ['Code delta', `+${pr.additions} / -${pr.deletions}`, 'var(--foreground)'],
              ].map(([label, value, color]) => (
                <div key={label as string} style={{ background: 'var(--secondary)', borderRadius: 5, padding: '12px 14px' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: 4 }}>
                    {label as string}
                  </div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 500, color: color as string }}>
                    {value as string}
                  </div>
                </div>
              ))}
            </div>

            <div className={`pr-findings-summary${pr.findings > 0 ? ' has-findings' : ''}`}>
              <ShieldAlert size={14} />
              <div>
                <span>Security findings</span>
                <strong>{findingsSummary(pr, analysisState)}</strong>
              </div>
              {pr.findings > 0 && (
                <button className="btn btn-ghost btn-sm" onClick={() => setTab('findings')}>
                  View findings
                </button>
              )}
            </div>

            {/* Human review decision */}
            {decision === 'pending' && analysisState === 'complete' && (
              <div className="pr-human-decision" style={{ border: '1px solid var(--border)', borderRadius: 5, padding: '14px 16px' }}>
                <div className="pr-human-decision-label">Human review required</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--foreground)', marginBottom: 4 }}>Make the final decision</div>
                <p style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)', margin: '0 0 14px', lineHeight: 1.65 }}>
                  AI analysis is complete. Review the security findings and make the final decision.
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-sm" onClick={() => setDecision('approved')} style={{ background: 'var(--status-safe)', color: '#000', fontWeight: 600 }}>
                    <CheckCircle size={12} /> Approve
                  </button>
                  <button className="btn btn-sm btn-secondary" onClick={() => setDecision('rejected')} style={{ borderColor: 'color-mix(in srgb, var(--status-warn) 40%, var(--border))', color: 'var(--status-warn)' }}>
                    <XCircle size={12} /> Request changes
                  </button>
                </div>
              </div>
            )}

            {decision !== 'pending' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: `color-mix(in srgb, ${decision === 'approved' ? 'var(--status-safe)' : 'var(--status-warn)'} 8%, var(--secondary))`, borderRadius: 5 }}>
                {decision === 'approved' ? <CheckCircle size={14} style={{ color: 'var(--status-safe)' }} /> : <XCircle size={14} style={{ color: 'var(--status-warn)' }} />}
                <span style={{ fontSize: '0.78rem', color: decision === 'approved' ? 'var(--status-safe)' : 'var(--status-warn)', fontWeight: 500 }}>
                  Final decision: {decision === 'approved' ? 'Approved' : 'Changes requested'}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Findings tab */}
        {tab === 'findings' && pr.findings === 0 && (
          <div className="empty-state" style={{ padding: '40px 20px' }}>
            <div className="empty-state-icon">
              <CheckCircle size={18} style={{ color: 'var(--status-safe)' }} />
            </div>
            <div className="empty-title">No security findings</div>
            <div className="empty-sub">Vigil's AI analysis did not surface security findings for this pull request.</div>
          </div>
        )}

        {tab === 'findings' && pr.findings_data.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {pr.findings_data.map((f, i) => (
              <div key={i} style={{ border: '1px solid var(--border)', borderRadius: 5, overflow: 'hidden' }}>
                <div style={{
                  padding: '10px 14px',
                  background: 'var(--secondary)',
                  borderBottom: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <ShieldAlert size={13} style={{ color: f.severity === 'critical' ? 'var(--status-critical)' : 'var(--status-high)' }} />
                  <SevBadge s={f.severity} />
                  <span style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--foreground)', flex: 1 }}>{f.title}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem', color: 'var(--muted-foreground)' }}>
                    {f.file}:{f.line}
                  </span>
                </div>
                <div style={{ padding: '12px 14px' }}>
                  <p style={{ fontSize: '0.75rem', color: 'var(--secondary-foreground)', lineHeight: 1.65, margin: '0 0 10px' }}>{f.desc}</p>
                  <div style={{ marginBottom: 10, padding: '8px 10px', background: 'var(--secondary)', borderRadius: 4 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--muted-foreground)' }}>Potential impact · </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--secondary-foreground)' }}>{f.impact}</span>
                  </div>
                  <div style={{ padding: '8px 10px', background: 'color-mix(in srgb, var(--ai) 6%, var(--secondary))', borderRadius: 4, borderLeft: '2px solid var(--ai)' }}>
                    <div className="ai-tag" style={{ marginBottom: 4, display: 'inline-flex' }}>Review guidance</div>
                    <p style={{ fontSize: '0.72rem', color: 'var(--secondary-foreground)', lineHeight: 1.6, margin: 0 }}>{f.fix}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Files tab */}
        {tab === 'files' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {['src/auth/jwt.go', 'src/middleware/auth.go', 'src/handlers/user.go', 'go.mod', 'go.sum', 'Makefile', 'README.md', 'config/default.yaml'].slice(0, pr.files).map(f => (
              <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', background: 'var(--secondary)', borderRadius: 4 }}>
                <FileCode size={12} style={{ color: 'var(--muted-foreground)' }} />
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--foreground)' }}>{f}</span>
              </div>
            ))}
          </div>
        )}

        {tab === 'commits' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              ['a3f9c12', 'Priya Sharma', 'Add JWT generation and signing'],
              ['7e2bd31', 'Priya Sharma', 'Add authentication middleware'],
              ['ac81f09', 'Rohan Mehta', 'Add refresh token handler'],
            ].map(([hash, author, message], index) => (
              <div key={hash} style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'var(--secondary)', borderRadius: 4 }}>
                <GitCommitHorizontal size={12} style={{ color: index === 0 && pr.findings > 0 ? 'var(--status-critical)' : 'var(--muted-foreground)' }} />
                <div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.7rem', color: 'var(--primary)' }}>{hash}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--secondary-foreground)' }}>{message} · {author}</div>
                </div>
                <span style={{ fontSize: '0.72rem', color: index === 0 && pr.findings > 0 ? 'var(--status-critical)' : 'var(--status-safe)' }}>
                  {index === 0 && pr.findings > 0 ? 'Finding associated' : 'No findings associated'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PullRequests() {
  const location = useLocation();
  const initialId = (location.state as { prId?: number } | null)?.prId;
  const [selected, setSelected] = useState(() => PRS.find(pr => pr.id === initialId) ?? PRS[0]);
  const [filter, setFilter] = useState<'all' | 'pending' | 'reviewed'>('all');

  const filtered = PRS.filter(pr =>
    filter === 'all' ? true :
    filter === 'pending' ? pr.humanStatus === 'pending' && pr.aiStatus === 'complete' :
    pr.humanStatus !== 'pending'
  );

  return (
    <div className="v-page stage3-page" style={{ maxWidth: 1160 }}>
      <PageHeader
        title="Pull Requests"
        subtitle="Review AI-analyzed pull requests and security findings"
      />

      <div className="stage3-filters" style={{ display: 'flex', gap: 6, marginBottom: 18 }}>
        {(['all', 'pending', 'reviewed'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} className="btn btn-sm" style={{
            background: filter === f ? 'var(--primary)' : 'transparent',
            color: filter === f ? '#fff' : 'var(--muted-foreground)',
            border: '1px solid var(--border)',
            textTransform: 'capitalize',
          }}>
            {f === 'all' ? 'All' : f === 'pending' ? 'Awaiting decision' : 'Reviewed'}
          </button>
        ))}
      </div>

      <div className="stage3-master-detail stage3-pr-layout" style={{ display: 'grid', gridTemplateColumns: '300px minmax(0, 1fr)', gap: 18, alignItems: 'start' }}>
        <div className="stage3-sticky-list" style={{ display: 'flex', flexDirection: 'column', gap: 8, position: 'sticky', top: 0 }}>
          {filtered.map(pr => (
            <PRListItem key={pr.id} pr={pr} active={selected.id === pr.id} onClick={() => setSelected(pr)} />
          ))}
          {filtered.length === 0 && (
            <div className="empty-state" style={{ padding: '36px 20px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6 }}>
              <GitPullRequest size={20} style={{ color: 'var(--muted-foreground)', marginBottom: 8 }} />
              <div className="empty-title">No pull requests awaiting review</div>
              <div className="empty-sub">New pull requests will appear here after Vigil begins analysis.</div>
            </div>
          )}
        </div>
        <PRDetail pr={selected} />
      </div>
    </div>
  );
}
