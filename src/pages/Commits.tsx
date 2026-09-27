import { useState } from 'react';
import { GitCommitHorizontal, AlertTriangle, CheckCircle, FileCode, Plus, Minus } from 'lucide-react';
import { OrbXS } from '../components/AIOrb';
import PageHeader from '../components/PageHeader';

const commits = [
  {
    hash: 'a3f9c12', fullHash: 'a3f9c128b4d21e7f903c4a18b5d9e2f041c7a8b3',
    message: 'fix: sanitize user input in search endpoint',
    author: 'Priya Sharma', email: 'priya@acme-corp.com',
    repo: 'api-gateway', branch: 'main', time: '1h ago', date: 'Sep 25, 2026',
    flagged: true, flags: ['Input validation change'],
    additions: 12, deletions: 3, files: 2,
    aiSummary: 'This commit adds input sanitization to the search endpoint. The change correctly uses html.EscapeString for output encoding. Review confirms no injection vectors introduced.',
    diff: `@@ -38,6 +38,18 @@ func SearchHandler(w http.ResponseWriter, r *http.Request) {
 	query := r.URL.Query().Get("q")
-	results := db.Search(query)
+	sanitized := html.EscapeString(query)
+	if len(sanitized) > 100 {
+		http.Error(w, "query too long", 400)
+		return
+	}
+	results := db.Search(sanitized)
 	json.NewEncoder(w).Encode(results)`,
  },
  {
    hash: 'b7d2e45', fullHash: 'b7d2e4578c3f91a0d2b6e8f4c1a7b9e0f23d5c6a',
    message: 'chore: bump dependencies',
    author: 'Rohan Mehta', email: 'rohan@acme-corp.com',
    repo: 'web-frontend', branch: 'main', time: '3h ago', date: 'Sep 25, 2026',
    flagged: false, flags: [],
    additions: 5, deletions: 5, files: 2,
    aiSummary: 'Routine dependency update. No security-sensitive packages changed. Lockfile updated to match.',
    diff: `@@ -18,6 +18,6 @@
-    "axios": "^1.4.0",
+    "axios": "^1.6.2",
     "react": "^19.0.0"`,
  },
  {
    hash: 'c1a8f67', fullHash: 'c1a8f67d2e9b3a4c5f1e8d7c0b2a4f6e8d9c1b3a',
    message: 'feat: add rate limiting to auth routes',
    author: 'Anita Bose', email: 'anita@acme-corp.com',
    repo: 'auth-service', branch: 'main', time: '5h ago', date: 'Sep 25, 2026',
    flagged: true, flags: ['Auth route modification', 'Middleware change'],
    additions: 34, deletions: 2, files: 3,
    aiSummary: 'Rate limiting added to /auth/login and /auth/refresh. Implementation uses an in-memory sliding window counter — note this will not work correctly in multi-instance deployments without a shared Redis store.',
    diff: `@@ -12,4 +12,14 @@ func AuthRoutes(r *gin.Engine) {
 	auth := r.Group("/auth")
+	auth.Use(rateLimiter.Limit(10, time.Minute))
 	auth.POST("/login", LoginHandler)
 	auth.POST("/refresh", RefreshHandler)`,
  },
];

export default function Commits() {
  const [selected, setSelected] = useState(commits[0]);

  return (
    <div className="stage3-page" style={{ padding: '32px 36px', maxWidth: '1200px' }}>
      <PageHeader
        title="Commit Analysis"
        subtitle="Security-focused review of recent commits"
      />

      <div className="stage3-master-detail" style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr)', gap: '20px' }}>
        {/* Commit list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {commits.map(c => (
            <div
              key={c.hash}
              onClick={() => setSelected(c)}
              style={{
                padding: '14px 16px',
                background: selected.hash === c.hash ? 'var(--secondary)' : 'var(--card)',
                border: `1px solid ${selected.hash === c.hash ? 'color-mix(in srgb, var(--primary) 30%, var(--border))' : 'var(--border)'}`,
                borderLeft: `2px solid ${selected.hash === c.hash ? 'var(--primary)' : c.flagged ? 'var(--severity-medium)' : 'transparent'}`,
                borderRadius: '8px', cursor: 'pointer', transition: 'all 150ms',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <GitCommitHorizontal size={12} style={{ color: c.flagged ? 'var(--severity-medium)' : 'var(--muted-foreground)' }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--primary)' }}>{c.hash}</span>
                {c.flagged && <AlertTriangle size={11} style={{ color: 'var(--severity-medium)', marginLeft: 'auto' }} />}
                {!c.flagged && <CheckCircle size={11} style={{ color: 'var(--accent)', marginLeft: 'auto' }} />}
              </div>
              <div style={{ fontSize: '0.8rem', fontWeight: '500', color: 'var(--foreground)', marginBottom: '4px', lineHeight: '1.4' }}>{c.message}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{c.repo} · {c.author} · {c.time}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: '0.7rem' }}>
                <span style={{ color: c.flagged ? 'var(--severity-medium)' : 'var(--accent)' }}>
                  {c.flagged ? `Concern introduced · ${c.flags.length} signal${c.flags.length === 1 ? '' : 's'}` : 'No findings'}
                </span>
                <span style={{ color: 'var(--muted-foreground)' }}>Analysis complete</span>
              </div>
              {c.flags.length > 0 && (
                <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {c.flags.map(f => (
                    <span key={f} style={{
                      fontSize: '0.7rem', padding: '2px 6px',
                      background: 'color-mix(in srgb, var(--severity-medium) 12%, transparent)',
                      color: 'var(--severity-medium)',
                      border: '1px solid color-mix(in srgb, var(--severity-medium) 30%, transparent)',
                      borderRadius: '4px',
                    }}>{f}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Commit detail */}
        <div style={{
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: '8px', overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--primary)' }}>{selected.fullHash.slice(0, 16)}...</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{selected.repo} · {selected.date}</span>
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: '600', color: 'var(--foreground)', margin: '0 0 8px' }}>{selected.message}</h3>
            <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
              <span>{selected.author} &lt;{selected.email}&gt;</span>
              <span style={{ color: 'var(--accent)' }}><Plus size={11} style={{ display: 'inline' }} />{selected.additions}</span>
              <span style={{ color: 'var(--severity-critical)' }}><Minus size={11} style={{ display: 'inline' }} />{selected.deletions}</span>
              <span><FileCode size={11} style={{ display: 'inline', marginRight: '3px' }} />{selected.files} files</span>
            </div>
          </div>

          {/* AI analysis */}
          <div style={{
            padding: '14px 24px', borderBottom: '1px solid var(--border)',
            background: selected.flagged
              ? 'color-mix(in srgb, var(--severity-medium) 5%, transparent)'
              : 'color-mix(in srgb, var(--accent) 5%, transparent)',
            display: 'flex', gap: '10px', alignItems: 'flex-start',
          }}>
            <OrbXS size={14} variant="active" style={{ marginTop: '1px', flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                AI Analysis
              </div>
              <p style={{ fontSize: '0.875rem', color: 'var(--secondary-foreground)', lineHeight: '1.6', margin: 0 }}>
                {selected.aiSummary}
              </p>
            </div>
          </div>

          {/* Security flags */}
          {selected.flags.length > 0 && (
            <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: '10px' }}>
                Security Signals
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selected.flags.map(f => (
                  <div key={f} style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '8px 12px',
                    background: 'color-mix(in srgb, var(--severity-medium) 8%, var(--secondary))',
                    border: '1px solid color-mix(in srgb, var(--severity-medium) 25%, transparent)',
                    borderRadius: '6px',
                  }}>
                    <AlertTriangle size={12} style={{ color: 'var(--severity-medium)' }} />
                    <span style={{ fontSize: '0.875rem', color: 'var(--foreground)' }}>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Diff */}
          <div style={{ padding: '20px 24px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: '10px' }}>
              Code Changes
            </div>
            <div className="commit-diff" style={{
              background: 'var(--code-background)', border: '1px solid var(--border)',
              borderRadius: '8px', overflow: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
              lineHeight: '1.6',
            }}>
              {selected.diff.split('\n').map((line, i) => {
                const isAdd = line.startsWith('+') && !line.startsWith('+++');
                const isDel = line.startsWith('-') && !line.startsWith('---');
                const isHunk = line.startsWith('@@');
                return (
                  <div
                    key={i}
                    style={{
                      padding: '1px 16px',
                      background: isAdd ? 'color-mix(in srgb, var(--accent) 10%, transparent)' : isDel ? 'color-mix(in srgb, var(--severity-critical) 10%, transparent)' : isHunk ? 'color-mix(in srgb, var(--primary) 8%, transparent)' : 'transparent',
                      color: isAdd ? 'var(--accent)' : isDel ? 'var(--severity-critical)' : isHunk ? 'var(--primary)' : 'var(--secondary-foreground)',
                      whiteSpace: 'pre',
                    }}
                  >
                    {line}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
