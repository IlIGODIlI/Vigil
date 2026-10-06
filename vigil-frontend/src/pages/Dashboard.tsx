import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitPullRequest, ShieldAlert, GitCommitHorizontal, CheckCircle, ArrowRight, AlertTriangle, LogOut, PlayCircle } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { useAuth } from '../auth/AuthContext';
import { useApp } from '../contexts/AppContext';
import darkBotImage from '../imports/dbot.png';
import lightBotImage from '../imports/lbot.png';
import GuidedTourModal from '../components/GuidedTourModal';

/* ── Shared micro-components ── */

function SevBadge({ s }: { s: string }) {
  const cls = s === 'critical' ? 'sev-critical' : s === 'high' ? 'sev-high' : s === 'medium' ? 'sev-medium' : s === 'low' ? 'sev-low' : 'sev-info';
  const lbl = s === 'critical' ? 'Crit' : s === 'high' ? 'High' : s === 'medium' ? 'Med' : s === 'low' ? 'Low' : 'Info';
  return <span className={`sev ${cls}`}>{lbl}</span>;
}

function HRule() {
  return <div className="divider" />;
}

/* ── Stat tile — minimal, no icon distraction ── */
function Stat({ label, value, sub, color }: { label: string; value: string; sub: string; color?: string }) {
  return (
    <div style={{ padding: '18px 20px' }}>
      <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted-foreground)', marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.6rem', fontWeight: 600, color: color ?? 'var(--foreground)', lineHeight: 1, marginBottom: 4 }}>
        {value}
      </div>
      <div style={{ fontSize: '0.7rem', color: 'var(--muted-foreground)' }}>{sub}</div>
    </div>
  );
}

/* ── Inline PR row ── */
function PRRow({ pr, onClick }: { pr: PR; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 12,
        padding: '12px 18px',
        cursor: 'pointer',
        transition: 'background 120ms',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--secondary)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>
            #{pr.id}
          </span>
          <SevBadge s={pr.severity} />
          {pr.aiStatus === 'analyzing' && (
            <span style={{ fontSize: '0.75rem', color: 'var(--ai)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className="dot dot-pulse" style={{ width: 5, height: 5, background: 'var(--ai)' }} />
              Analyzing
            </span>
          )}
          {pr.humanStatus === 'approved' && (
            <CheckCircle size={11} style={{ color: 'var(--status-safe)' }} />
          )}
        </div>
        <div style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--foreground)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 2 }}>
          {pr.title}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--muted-foreground)' }}>
          {pr.repo} · {pr.author} · {pr.time}
          {pr.findings > 0 && <span style={{ color: 'var(--status-critical)', marginLeft: 8 }}>⚑ {pr.findings}</span>}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', color: 'var(--muted-foreground)' }}>
        <ArrowRight size={13} />
      </div>
    </div>
  );
}

/* ── Commit row ── */
function CommitRow({ c, onClick }: { c: Commit; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: 'auto 1fr auto',
        gap: 10,
        padding: '10px 18px',
        alignItems: 'center',
        cursor: 'pointer',
        transition: 'background 120ms',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--secondary)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <GitCommitHorizontal
        size={13}
        style={{ color: c.flagged ? 'var(--status-warn)' : 'var(--muted-foreground)', flexShrink: 0 }}
      />
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 1 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--primary)' }}>{c.hash}</span>
          {c.flagged && <span className="sev sev-medium">flagged</span>}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--secondary-foreground)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {c.message}
        </div>
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)', flexShrink: 0 }}>{c.time}</div>
    </div>
  );
}

/* ── Types ── */
interface PR { id: number; title: string; repo: string; author: string; severity: string; aiStatus: string; humanStatus: string; findings: number; time: string; }
interface Commit { hash: string; message: string; repo: string; flagged: boolean; time: string; }

/* ── Data ── */
const PRS: PR[] = [
  { id: 47, title: 'feat: add user authentication via JWT', repo: 'api-gateway', author: 'Priya Sharma', severity: 'critical', aiStatus: 'complete', humanStatus: 'pending', findings: 2, time: '2h ago' },
  { id: 51, title: 'fix: update axios dependency to 1.6.2', repo: 'web-frontend', author: 'Rohan Mehta', severity: 'medium', aiStatus: 'complete', humanStatus: 'pending', findings: 1, time: '4h ago' },
  { id: 43, title: 'refactor: extract auth middleware', repo: 'auth-service', author: 'Anita Bose', severity: 'low', aiStatus: 'analyzing', humanStatus: 'pending', findings: 0, time: '6h ago' },
  { id: 39, title: 'chore: update CI pipeline config', repo: 'infrastructure', author: 'Dev Kapoor', severity: 'info', aiStatus: 'complete', humanStatus: 'approved', findings: 0, time: '1d ago' },
];

const COMMITS: Commit[] = [
  { hash: 'a3f9c12', message: 'fix: sanitize user input in search endpoint', repo: 'api-gateway', flagged: true, time: '1h' },
  { hash: 'b7d2e45', message: 'chore: bump dependencies', repo: 'web-frontend', flagged: false, time: '3h' },
  { hash: 'c1a8f67', message: 'feat: add rate limiting to auth routes', repo: 'auth-service', flagged: true, time: '5h' },
  { hash: 'd4e1b89', message: 'docs: update API reference', repo: 'api-gateway', flagged: false, time: '8h' },
];

const REPO_SCORES = [
  { name: 'api-gateway',   score: 42, status: 'critical' },
  { name: 'auth-service',  score: 68, status: 'medium' },
  { name: 'web-frontend',  score: 84, status: 'low' },
  { name: 'data-pipeline', score: 91, status: 'safe' },
];

function scoreColor(status: string) {
  return status === 'critical' ? 'var(--status-critical)' : status === 'medium' ? 'var(--status-warn)' : status === 'low' ? 'var(--status-low)' : 'var(--status-safe)';
}

/* ── Page ── */
export default function Dashboard() {
  const navigate = useNavigate();
  const { user, signOut, isLoading: authLoading } = useAuth();
  const { t, theme } = useApp();
  const pendingPRs = PRS.filter(p => p.humanStatus === 'pending');
  const firstName = user?.displayName.split(' ')[0] || 'there';
  const [tourOpen, setTourOpen] = useState(false);

  return (
    <div className="v-page stage3-page dashboard-page">

      {/* Header */}
      <PageHeader
        title={t('dashboard')}
        subtitle={`Sep 25, 2026 · ${t('goodMorning')}, ${firstName}`}
        actions={
          <div className="dashboard-header-actions">
            <div className="dashboard-ai-active">
              <span className="dot dot-safe dot-pulse" />
              <span>{t('aiActive')}</span>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => setTourOpen(true)}>
              <PlayCircle size={13} />
              {t('giveTour')}
            </button>
            <button className="btn btn-ghost btn-sm dashboard-signout" disabled={authLoading} onClick={() => void signOut()}>
              <LogOut size={13} />
              {t('signOut')}
            </button>
          </div>
        }
      />

      {/* ── Attention band ── */}
      {pendingPRs.filter(p => p.findings > 0).length > 0 && (
        <div className="stage3-attention" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '16px 18px',
          background: 'color-mix(in srgb, var(--status-critical) 7%, var(--card))',
          border: '1px solid color-mix(in srgb, var(--status-critical) 20%, transparent)',
          borderRadius: 5,
          marginBottom: 18,
        }}>
          <AlertTriangle size={14} style={{ color: 'var(--status-critical)', flexShrink: 0 }} />
          <span style={{ fontSize: '0.82rem', color: 'var(--foreground)', flex: 1 }}>
            <strong>{t('attentionMessage')}</strong>
          </span>
          <button
            className="btn btn-sm"
            onClick={() => navigate('/findings')}
            style={{ background: 'var(--status-critical)', color: '#fff', fontWeight: 500 }}
          >
            {t('reviewNow')}
          </button>
        </div>
      )}

      {/* ── Primary review grid ── */}
      <div className="stage3-primary-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 20 }}>

        {/* ── Left column ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Pull Requests panel */}
          <div className="dashboard-review-panel" style={{
            background: 'var(--card)',
            border: '1px solid color-mix(in srgb, var(--status-critical) 18%, var(--border))',
            borderRadius: 6,
            overflow: 'hidden',
            minHeight: '100%',
          }}>
            <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <GitPullRequest size={14} style={{ color: 'var(--muted-foreground)' }} strokeWidth={1.75} />
                <span className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>{t('pullRequests')}</span>
                <span style={{
                  fontSize: '0.75rem', fontWeight: 600,
                  background: 'color-mix(in srgb, var(--primary) 14%, transparent)',
                  color: 'var(--primary)',
                  padding: '1px 6px', borderRadius: 3,
                }}>
                  {PRS.filter(p => p.humanStatus === 'pending').length} {t('pending')}
                </span>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate('/pull-requests')}>
                {t('viewAll')} <ArrowRight size={11} />
              </button>
            </div>
            {PRS.map((pr, i) => (
              <div key={pr.id}>
                <PRRow pr={pr} onClick={() => navigate('/pull-requests', { state: { prId: pr.id } })} />
                {i < PRS.length - 1 && <HRule />}
              </div>
            ))}
          </div>
        </div>

        {/* Main security / analysis status */}
        <div className="dashboard-ai-status" style={{
          background: 'var(--card)',
          border: '1px solid color-mix(in srgb, var(--ai) 24%, var(--border))',
          borderRadius: 6,
          padding: '18px',
          alignSelf: 'stretch',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
            <img
              className="dashboard-ai-bot-image"
              src={theme === 'light' ? lightBotImage : darkBotImage}
              alt=""
              aria-hidden="true"
            />
            <div>
              <div className="ai-tag" style={{ marginBottom: 3 }}>{t('vigilAI')}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--secondary-foreground)' }}>{t('analysisInProgress')}</div>
            </div>
          </div>
          <div style={{
            background: 'color-mix(in srgb, var(--ai) 6%, var(--secondary))',
            border: '1px solid color-mix(in srgb, var(--ai) 15%, transparent)',
            borderRadius: 4,
            padding: '12px',
            marginBottom: 16,
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted-foreground)', marginBottom: 2 }}>{t('analyzing')}</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--ai)' }}>
              PR #43 · auth-service
            </div>
          </div>
          <div style={{ height: 2, background: 'var(--secondary)', borderRadius: 1, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: '65%',
              background: `linear-gradient(90deg, var(--ai), var(--primary))`,
              borderRadius: 1,
              animation: 'progress-fill 1.2s ease forwards',
            }} />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)', marginTop: 6, textAlign: 'right' }}>
            {t('remaining')}
          </div>
        </div>
      </div>

      {/* ── Secondary metrics ── */}
      <div className="stage3-stat-grid dashboard-metrics" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        margin: '20px 0',
        overflow: 'hidden',
      }}>
        {[
          { label: t('openPRs'), value: '7', sub: t('needDecision'), color: undefined },
          { label: t('criticalFindings'), value: '2', sub: t('acrossRepos'), color: 'var(--status-critical)' },
          { label: t('reviewedToday'), value: '5', sub: t('fromYesterday'), color: undefined },
          { label: t('averageReviewTime'), value: '4.2h', sub: t('lastSevenDays'), color: undefined },
        ].map((s, i) => (
          <div key={s.label} style={{ borderRight: i < 3 ? '1px solid var(--border)' : 'none' }}>
            <Stat {...s} />
          </div>
        ))}
      </div>

      {/* ── Supporting information ── */}
      <div className="stage3-support-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 20 }}>
        <div>
          {/* Recent commits */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
            <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <GitCommitHorizontal size={14} style={{ color: 'var(--muted-foreground)' }} strokeWidth={1.75} />
                <span className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>{t('recentCommits')}</span>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate('/commits')}>
                {t('viewAll')} <ArrowRight size={11} />
              </button>
            </div>
            {COMMITS.map((c, i) => (
              <div key={c.hash}>
                <CommitRow c={c} onClick={() => navigate('/commits')} />
                {i < COMMITS.length - 1 && <HRule />}
              </div>
            ))}
          </div>
        </div>

        {/* ── Supporting right column ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Security posture */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
            <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 7 }}>
              <ShieldAlert size={14} style={{ color: 'var(--muted-foreground)' }} strokeWidth={1.75} />
              <span className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>{t('securityPosture')}</span>
            </div>
            <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              {REPO_SCORES.map(({ name, score, status }) => (
                <div key={name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem', color: 'var(--secondary-foreground)' }}>
                      {name}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem', fontWeight: 600, color: scoreColor(status) }}>
                      {score}
                    </span>
                  </div>
                  <div style={{ height: 3, background: 'var(--secondary)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${score}%`,
                      background: scoreColor(status),
                      borderRadius: 2,
                      animation: 'progress-fill 800ms ease forwards',
                    }} />
                  </div>
                </div>
              ))}
            </div>
            <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border)' }}>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate('/repositories')} style={{ width: '100%', justifyContent: 'center' }}>
                {t('allRepositories')} <ArrowRight size={11} />
              </button>
            </div>
          </div>

          {/* Review activity */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
            <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)' }}>
              <span className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>{t('reviewActivity')}</span>
            </div>
            <div style={{ padding: '4px 0' }}>
              {[
                { label: t('approved'), count: 12, color: 'var(--status-safe)' },
                { label: t('changesRequested'), count: 5, color: 'var(--status-warn)' },
                { label: t('escalated'), count: 2, color: 'var(--status-critical)' },
                { label: t('inProgress'), count: 3, color: 'var(--primary)' },
              ].map(({ label, count, color }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                    <div style={{ width: 6, height: 6, borderRadius: 2, background: color, flexShrink: 0 }} />
                    <span style={{ fontSize: '0.78rem', color: 'var(--secondary-foreground)' }}>{label}</span>
                  </div>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>{count}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
      {tourOpen && <GuidedTourModal onClose={() => setTourOpen(false)} />}
    </div>
  );
}
