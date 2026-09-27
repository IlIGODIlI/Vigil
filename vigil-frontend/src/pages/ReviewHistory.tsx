import { useState } from 'react';
import { CheckCircle, XCircle, Clock, ArrowUpRight, User, ShieldAlert } from 'lucide-react';
import { OrbXS } from '../components/AIOrb';
import PageHeader from '../components/PageHeader';

const reviews = [
  {
    id: 'R-028', pr: 39, title: 'chore: update CI pipeline config', repo: 'infrastructure',
    reviewer: 'Dev Kapoor', decision: 'approved', findings: 0,
    date: 'Sep 24, 2026', time: '14:32', duration: '12 min',
    aiStatus: 'complete', humanNote: 'CI config changes look safe. No security-relevant modifications.',
  },
  {
    id: 'R-027', pr: 35, title: 'feat: add OAuth2 provider support', repo: 'auth-service',
    reviewer: 'Priya Sharma', decision: 'changes_requested', findings: 2,
    date: 'Sep 23, 2026', time: '16:45', duration: '28 min',
    aiStatus: 'complete', humanNote: 'OAuth state parameter not validated. Potential CSRF in auth flow. Must fix before merge.',
  },
  {
    id: 'R-026', pr: 31, title: 'fix: resolve memory leak in cache', repo: 'api-gateway',
    reviewer: 'Rohan Mehta', decision: 'approved', findings: 0,
    date: 'Sep 22, 2026', time: '10:18', duration: '8 min',
    aiStatus: 'complete', humanNote: 'Memory management fix. AI confirmed no security implications.',
  },
  {
    id: 'R-025', pr: 28, title: 'feat: add export to CSV endpoint', repo: 'data-pipeline',
    reviewer: 'Anita Bose', decision: 'escalated', findings: 1,
    date: 'Sep 21, 2026', time: '11:54', duration: '19 min',
    aiStatus: 'complete', humanNote: 'Possible CSV injection — escalated to senior review.',
  },
  {
    id: 'R-024', pr: 25, title: 'deps: upgrade SQLAlchemy to 2.0', repo: 'auth-service',
    reviewer: 'Dev Kapoor', decision: 'approved', findings: 0,
    date: 'Sep 20, 2026', time: '09:10', duration: '15 min',
    aiStatus: 'complete', humanNote: 'Dependency upgrade verified against changelog. No breaking security changes.',
  },
];

const decisionConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  approved: { label: 'Approved', icon: CheckCircle, color: 'var(--accent)' },
  changes_requested: { label: 'Changes Requested', icon: XCircle, color: 'var(--severity-medium)' },
  escalated: { label: 'Escalated', icon: ArrowUpRight, color: 'var(--severity-critical)' },
  pending: { label: 'Pending', icon: Clock, color: 'var(--primary)' },
};

export default function ReviewHistory() {
  const [filter, setFilter] = useState<'all' | 'approved' | 'changes_requested' | 'escalated'>('all');
  const visibleReviews = reviews.filter(review => filter === 'all' || review.decision === filter);

  return (
    <div className="stage3-page" style={{ padding: '32px 36px', maxWidth: '1000px' }}>
      <PageHeader
        title="Review History"
        subtitle="Complete audit trail of security reviews"
      />

      {/* Summary stats */}
      <div className="stage3-stat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
        {[
          ['28', 'Total Reviews', 'This month'],
          ['4.2h', 'Avg. Resolution', 'Time to decision'],
          ['87%', 'Approval Rate', 'Last 30 days'],
          ['3', 'Escalated', 'Sent to senior'],
        ].map(([val, label, sub]) => (
          <div key={label} style={{
            background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: '8px', padding: '16px',
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: '600', color: 'var(--foreground)', marginBottom: '4px' }}>{val}</div>
            <div style={{ fontSize: '0.8rem', fontWeight: '500', color: 'var(--foreground)', marginBottom: '2px' }}>{label}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{sub}</div>
          </div>
        ))}
      </div>

      <div className="stage3-filters" style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {(['all', 'approved', 'changes_requested', 'escalated'] as const).map(value => (
          <button
            key={value}
            className="btn btn-sm"
            onClick={() => setFilter(value)}
            style={{
              background: filter === value ? 'var(--primary)' : 'transparent',
              color: filter === value ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
              border: '1px solid var(--border)',
            }}
          >
            {value === 'all' ? 'All decisions' : decisionConfig[value].label}
          </button>
        ))}
      </div>

      {/* Timeline */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {visibleReviews.map((r) => {
          const dcfg = decisionConfig[r.decision];
          const DIcon = dcfg.icon;

          return (
            <div
              key={r.id}
              style={{
                background: 'var(--card)', border: '1px solid var(--border)',
                borderRadius: '8px', overflow: 'hidden',
                transition: 'border-color 150ms', cursor: 'pointer',
              }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--primary) 30%, var(--border))')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
            >
              {/* Status stripe */}
              <div style={{ height: '2px', background: dcfg.color }} />

              <div style={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{r.id}</span>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '4px',
                        padding: '2px 8px',
                        background: `color-mix(in srgb, ${dcfg.color} 12%, transparent)`,
                        border: `1px solid color-mix(in srgb, ${dcfg.color} 30%, transparent)`,
                        borderRadius: '4px',
                      }}>
                        <DIcon size={10} style={{ color: dcfg.color }} />
                        <span style={{ fontSize: '0.7rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', color: dcfg.color }}>
                          {dcfg.label}
                        </span>
                      </div>
                      {r.findings > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <ShieldAlert size={11} style={{ color: 'var(--severity-medium)' }} />
                          <span style={{ fontSize: '0.75rem', color: 'var(--severity-medium)' }}>{r.findings} finding{r.findings > 1 ? 's' : ''}</span>
                        </div>
                      )}
                    </div>

                    <div style={{ fontSize: '0.9rem', fontWeight: '500', color: 'var(--foreground)', marginBottom: '4px' }}>
                      {r.title}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)', marginBottom: '12px' }}>
                      {r.repo} · PR #{r.pr} · {r.date} at {r.time} · {r.duration}
                    </div>

                    {/* Notes */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                        <OrbXS size={12} variant="active" style={{ marginTop: '2px', flexShrink: 0 }} />
                        <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
                          AI analysis complete — {r.findings === 0 ? 'no findings detected' : `${r.findings} issue${r.findings > 1 ? 's' : ''} flagged`}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                        <User size={12} style={{ color: 'var(--secondary-foreground)', marginTop: '2px', flexShrink: 0 }} />
                        <span style={{ fontSize: '0.8rem', color: 'var(--secondary-foreground)', fontStyle: 'italic' }}>
                          "{r.humanNote}"
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Reviewer */}
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--foreground)', fontWeight: '500' }}>{r.reviewer}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>Reviewer</div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
