import { Fragment, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, AlertTriangle, Info, CheckCircle, Code2, ArrowRight, GitPullRequest } from 'lucide-react';
import { OrbXS } from '../components/AIOrb';
import PageHeader from '../components/PageHeader';

const findings = [
  {
    id: 'F-001', severity: 'critical', title: 'Hardcoded JWT signing secret',
    file: 'src/auth/jwt.go', line: 42, repo: 'api-gateway', pr: 47, prTitle: 'feat: add user authentication via JWT',
    status: 'open', timestamp: '2h ago',
    description: 'A JWT signing secret ("supersecret123") is hardcoded as a string literal. This exposes the secret in version control history and makes rotation impossible without a code change.',
    impact: 'An attacker who obtains the source code or git history can forge JWT tokens, effectively becoming any user in the system.',
    fix: 'Move the secret to an environment variable (e.g. JWT_SECRET) and load it at runtime. Rotate the current secret immediately as it should be considered compromised.',
    codeSnippet: 'var jwtSecret = []byte("supersecret123")',
    fixSnippet: 'var jwtSecret = []byte(os.Getenv("JWT_SECRET"))',
  },
  {
    id: 'F-002', severity: 'critical', title: 'Missing token expiry validation',
    file: 'src/middleware/auth.go', line: 78, repo: 'api-gateway', pr: 47, prTitle: 'feat: add user authentication via JWT',
    status: 'open', timestamp: '2h ago',
    description: 'JWT tokens are validated for signature integrity but the expiry claim (exp) is not checked. A stolen token remains valid indefinitely.',
    impact: 'Stolen tokens cannot be invalidated. Users who report account compromise cannot be protected.',
    fix: 'Add expiry validation using jwt.WithExpirationRequired() or manually check the exp claim after parsing.',
    codeSnippet: 'token, err := jwt.Parse(tokenStr, keyFunc)',
    fixSnippet: 'token, err := jwt.Parse(tokenStr, keyFunc, jwt.WithExpirationRequired())',
  },
  {
    id: 'F-003', severity: 'medium', title: 'Vulnerable axios version (CVE-2023-45857)',
    file: 'package.json', line: 18, repo: 'web-frontend', pr: 51, prTitle: 'fix: update axios dependency to 1.6.2',
    status: 'open', timestamp: '4h ago',
    description: 'axios 1.4.0 is vulnerable to CVE-2023-45857, which allows sensitive headers to be leaked cross-origin via XSRF token.',
    impact: 'CSRF tokens and authorization headers may be exposed to third-party origins in certain configurations.',
    fix: 'Upgrade axios to version 1.6.2 or later. Run: npm install axios@latest',
    codeSnippet: '"axios": "^1.4.0"',
    fixSnippet: '"axios": "^1.6.2"',
  },
  {
    id: 'F-004', severity: 'low', title: 'Overly broad CORS configuration',
    file: 'src/server/config.go', line: 23, repo: 'auth-service', pr: 52, prTitle: 'fix: restrict production CORS origins',
    status: 'open', timestamp: '1d ago',
    description: 'CORS is configured to allow all origins (*). This is acceptable in development but should be restricted in production.',
    impact: 'Low risk if deployment is isolated, but should be addressed before public exposure.',
    fix: 'Replace the wildcard with an explicit list of allowed origins.',
    codeSnippet: 'AllowOrigins: []string{"*"}',
    fixSnippet: 'AllowOrigins: []string{"https://app.acme-corp.com"}',
  },
];

const severityConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  critical: { icon: ShieldAlert, color: 'var(--severity-critical)', label: 'Critical' },
  high: { icon: AlertTriangle, color: 'var(--severity-high)', label: 'High' },
  medium: { icon: AlertTriangle, color: 'var(--severity-medium)', label: 'Medium' },
  low: { icon: Info, color: 'var(--severity-low)', label: 'Low' },
};

export default function Findings() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<(typeof findings)[number] | null>(findings[0]);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  const openFindings = findings.filter(finding => finding.status === 'open');
  const filtered = openFindings.filter(f => filter === 'all' || f.severity === filter);

  const cfg = severityConfig[selected?.severity ?? 'critical'];
  const Icon = cfg.icon;

  return (
    <div className="stage3-page" style={{ padding: '32px 36px', maxWidth: '1200px' }}>
      <PageHeader
        title="Security Findings"
        subtitle={`${openFindings.length} open findings across ${new Set(openFindings.map(f => f.repo)).size} repositories · Detected during AI analysis`}
      />

      {/* Severity summary */}
      <div className="stage3-severity-summary" style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
        {(['critical', 'high', 'medium', 'low'] as const).map(s => {
          const count = openFindings.filter(f => f.severity === s).length;
          const c = severityConfig[s];
          const SummaryIcon = c.icon;
          return (
            <div key={s} className={`finding-summary-card severity-${s}`} style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '8px 14px', background: 'var(--card)',
              border: '1px solid var(--border)', borderRadius: '6px',
            }}>
              <SummaryIcon size={14} style={{ color: c.color }} />
              <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>{c.label}</span>
              <span style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--foreground)', fontFamily: 'var(--font-mono)' }}>{count}</span>
            </div>
          );
        })}
      </div>

      <div className="stage3-filters" style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        {(['all', 'critical', 'high', 'medium', 'low'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '6px 14px', borderRadius: '6px', border: '1px solid var(--border)',
            background: filter === f ? 'var(--primary)' : 'transparent',
            color: filter === f ? '#fff' : 'var(--muted-foreground)',
            fontSize: '0.8rem', cursor: 'pointer', textTransform: 'capitalize',
          }}>{f}</button>
        ))}
      </div>

      <div className="stage3-master-detail" style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr)', gap: '20px' }}>
        {/* Findings list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filtered.map((f, index) => {
            const c = severityConfig[f.severity];
            const FIcon = c.icon;
            return (
              <Fragment key={f.id}>
                {(index === 0 || filtered[index - 1].severity !== f.severity) && (
                  <div style={{ padding: '5px 2px 1px', fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: c.color }}>
                    {c.label} severity
                  </div>
                )}
                <div
                className={`finding-list-card severity-${f.severity}${selected?.id === f.id ? ' selected' : ''}`}
                onClick={() => setSelected(current => current?.id === f.id ? null : f)}
                style={{
                  padding: '14px 16px',
                  background: selected?.id === f.id ? 'var(--secondary)' : 'var(--card)',
                  border: `1px solid ${selected?.id === f.id ? `color-mix(in srgb, ${c.color} 30%, var(--border))` : 'var(--border)'}`,
                  borderLeft: `2px solid ${selected?.id === f.id ? c.color : 'transparent'}`,
                  borderRadius: '8px', cursor: 'pointer', transition: 'all 150ms',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <FIcon size={12} style={{ color: c.color }} />
                  <span style={{ fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: c.color }}>{c.label}</span>
                  <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--muted-foreground)' }}>{f.id}</span>
                </div>
                <div style={{ fontSize: '0.84rem', fontWeight: '600', color: 'var(--foreground)', marginBottom: '4px', lineHeight: '1.4' }}>{f.title}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--muted-foreground)', marginBottom: 5 }}>{f.file}:{f.line}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: '0.7rem', color: 'var(--muted-foreground)' }}>
                  <span>{f.repo} · {f.status === 'open' ? 'Open' : f.status}</span>
                  <span>{f.timestamp}</span>
                </div>
                </div>
              </Fragment>
            );
          })}

          {filtered.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px' }}>
              <CheckCircle size={24} style={{ color: 'var(--accent)', marginBottom: '8px' }} />
              <div style={{ fontSize: '0.875rem', color: 'var(--foreground)' }}>No findings in this filter</div>
            </div>
          )}
        </div>

        {/* Finding detail */}
        {selected ? <div className={`finding-detail severity-${selected.severity}`} style={{
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: '8px', overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '4px 10px',
                background: `color-mix(in srgb, ${cfg.color} 12%, transparent)`,
                border: `1px solid color-mix(in srgb, ${cfg.color} 30%, transparent)`,
                borderRadius: '4px',
              }}>
                <Icon size={12} style={{ color: cfg.color }} />
                <span style={{ fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: cfg.color }}>{cfg.label}</span>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{selected.id}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{selected.repo}</span>
              <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--status-warn)' }}>Open</span>
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--foreground)', margin: '0 0 8px' }}>{selected.title}</h3>
            <div className="finding-context">
              <div><GitPullRequest size={12} /><strong>PR #{selected.pr}</strong><span>{selected.prTitle}</span></div>
              <div><Code2 size={12} /><strong>{selected.repo}</strong><span style={{ fontFamily: 'var(--font-mono)' }}>{selected.file}:{selected.line}</span></div>
            </div>
          </div>

          <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Description */}
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: '8px' }}>What was detected</div>
              <p style={{ fontSize: '0.875rem', color: 'var(--secondary-foreground)', lineHeight: '1.7', margin: 0 }}>{selected.description}</p>
            </div>

            {/* Impact */}
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: '8px' }}>Potential impact</div>
              <div style={{
                background: `color-mix(in srgb, ${cfg.color} 6%, var(--secondary))`,
                border: `1px solid color-mix(in srgb, ${cfg.color} 20%, var(--border))`,
                borderRadius: '6px', padding: '12px 14px',
              }}>
                <p style={{ fontSize: '0.875rem', color: 'var(--foreground)', lineHeight: '1.6', margin: 0 }}>{selected.impact}</p>
              </div>
            </div>

            {/* Code */}
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: '8px' }}>Affected code</div>
              <div className="finding-code" style={{ background: 'var(--code-background)', border: '1px solid var(--border)', borderRadius: '6px', padding: '12px 14px', overflow: 'auto' }}>
                <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: cfg.color }}>{selected.codeSnippet}</code>
              </div>
            </div>

            {/* Fix */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: '8px' }}>
                <OrbXS size={11} variant="active" />
                AI Suggested Remediation
              </div>
              <p style={{ fontSize: '0.875rem', color: 'var(--secondary-foreground)', lineHeight: '1.6', margin: '0 0 10px' }}>{selected.fix}</p>
              <div className="finding-code" style={{ background: 'var(--code-background)', border: '1px solid color-mix(in srgb, var(--accent) 30%, var(--border))', borderRadius: '6px', padding: '12px 14px' }}>
                <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: 'var(--accent)' }}>{selected.fixSnippet}</code>
              </div>
            </div>

            {/* Actions */}
            <div className="finding-human-action">
              <div>
                <strong>Human action</strong>
                <span>Review this finding in the originating pull request before making the final decision.</span>
              </div>
              <button
                className="btn btn-primary"
                onClick={() => navigate('/pull-requests', { state: { prId: selected.pr } })}
              >
                <Code2 size={13} /> View in PR <ArrowRight size={12} />
              </button>
            </div>
          </div>
        </div> : (
          <div className="empty-state" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <ShieldAlert size={22} style={{ color: 'var(--muted-foreground)', marginBottom: 10 }} />
            <div className="empty-title">Select a security finding</div>
            <div className="empty-sub">Expand a finding to review its explanation, impact, affected code, and suggested remediation.</div>
          </div>
        )}
      </div>
    </div>
  );
}
