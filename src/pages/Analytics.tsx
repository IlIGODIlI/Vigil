import { useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import PageHeader from '../components/PageHeader';

/* ── SVG Sparkline ── */
function Sparkline({ data, color, height = 48, width = 200 }: { data: number[]; color: string; height?: number; width?: number }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pad = 4;
  const W = width; const H = height;
  const xStep = (W - pad * 2) / (data.length - 1);

  const points = data.map((v, i) => ({
    x: pad + i * xStep,
    y: H - pad - ((v - min) / range) * (H - pad * 2),
  }));

  const polyline = points.map(p => `${p.x},${p.y}`).join(' ');
  const area = `${points[0].x},${H} ` + polyline + ` ${points[points.length - 1].x},${H}`;

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={`g-${color.replace(/[^a-z0-9]/gi, '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#g-${color.replace(/[^a-z0-9]/gi, '')})`} />
      <polyline points={polyline} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      {/* Last dot */}
      <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r={3} fill={color} />
    </svg>
  );
}

/* ── Trend indicator ── */
function Trend({ value, invert = false }: { value: number; invert?: boolean }) {
  const up = value > 0;
  const good = invert ? !up : up;
  const color = good ? 'var(--status-safe)' : value === 0 ? 'var(--muted-foreground)' : 'var(--status-critical)';
  const Icon = value === 0 ? Minus : up ? TrendingUp : TrendingDown;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color, fontSize: '0.72rem', fontWeight: 500 }}>
      <Icon size={12} />
      {value > 0 ? '+' : ''}{value}%
    </span>
  );
}

/* ── Metric card ── */
function MetricCard({ label, value, unit, trend, invert, spark, sparkColor }: {
  label: string; value: string; unit?: string; trend: number; invert?: boolean; spark: number[]; sparkColor: string;
}) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, padding: '18px 20px' }}>
      <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted-foreground)', marginBottom: 10 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.8rem', fontWeight: 600, color: 'var(--foreground)', lineHeight: 1 }}>
            {value}
          </span>
          {unit && <span style={{ fontSize: '0.78rem', color: 'var(--muted-foreground)', marginLeft: 4 }}>{unit}</span>}
        </div>
        <Trend value={trend} invert={invert} />
      </div>
      <Sparkline data={spark} color={sparkColor} width={180} height={44} />
    </div>
  );
}

/* ── Horizontal bar chart ── */
function BarChart({ data }: { data: { label: string; value: number; color: string }[] }) {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {data.map(({ label, value, color }) => (
        <div key={label}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--secondary-foreground)' }}>{label}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem', fontWeight: 600, color: 'var(--foreground)' }}>{value}</span>
          </div>
          <div style={{ height: 4, background: 'var(--secondary)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${(value / max) * 100}%`,
              background: color,
              borderRadius: 2,
              transition: 'width 600ms ease',
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Line chart (multi-series, SVG) ── */
function LineChart({ series, labels, height = 160 }: {
  series: { name: string; data: number[]; color: string }[];
  labels: string[];
  height?: number;
}) {
  const allValues = series.flatMap(s => s.data);
  const max = Math.max(...allValues);
  const min = 0;
  const range = max || 1;
  const W = 100; const H = height;
  const padX = 4; const padY = 8;
  const xStep = (W - padX * 2) / (labels.length - 1);

  const pts = (data: number[]) => data.map((v, i) => ({
    x: padX + i * xStep,
    y: H - padY - ((v - min) / range) * (H - padY * 2),
  }));

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block', overflow: 'visible' }}>
        {/* Horizontal grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(t => {
          const y = H - padY - t * (H - padY * 2);
          return (
            <line key={t} x1={padX} y1={y} x2={W - padX} y2={y}
              stroke="var(--border)" strokeWidth="0.5" />
          );
        })}

        {series.map(s => {
          const points = pts(s.data);
          const polyline = points.map(p => `${p.x},${p.y}`).join(' ');
          const area = `${points[0].x},${H - padY} ` + polyline + ` ${points[points.length - 1].x},${H - padY}`;
          const id = `area-${s.name.replace(/\s+/g, '')}`;
          return (
            <g key={s.name}>
              <defs>
                <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity="0.15" />
                  <stop offset="100%" stopColor={s.color} stopOpacity="0" />
                </linearGradient>
              </defs>
              <polygon points={area} fill={`url(#${id})`} />
              <polyline points={polyline} fill="none" stroke={s.color} strokeWidth="1.5" strokeLinejoin="round" />
            </g>
          );
        })}
      </svg>

      {/* X labels */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        {labels.map((l, i) => (
          <span key={i} style={{ fontSize: '0.7rem', color: 'var(--muted-foreground)', fontFamily: 'JetBrains Mono, monospace' }}>
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Data ── */
const WEEKS = ['Sep 1', 'Sep 8', 'Sep 15', 'Sep 22', 'Sep 25'];
const findingsSeries = [
  { name: 'Critical', data: [4, 6, 3, 5, 2], color: 'var(--status-critical)' },
  { name: 'Medium', data: [8, 10, 7, 9, 6], color: 'var(--status-warn)' },
  { name: 'Low', data: [12, 9, 11, 8, 10], color: 'var(--status-low)' },
];

const severityDist = [
  { label: 'Critical', value: 2,  color: 'var(--status-critical)' },
  { label: 'High',     value: 4,  color: 'var(--status-high)' },
  { label: 'Medium',   value: 6,  color: 'var(--status-warn)' },
  { label: 'Low',      value: 10, color: 'var(--status-low)' },
  { label: 'Info',     value: 3,  color: 'var(--status-info)' },
];

const repoActivity = [
  { repo: 'api-gateway',   prs: 18, findings: 12, resolved: 8,  score: 42 },
  { repo: 'auth-service',  prs: 11, findings: 5,  resolved: 4,  score: 68 },
  { repo: 'web-frontend',  prs: 14, findings: 3,  resolved: 3,  score: 84 },
  { repo: 'data-pipeline', prs: 6,  findings: 0,  resolved: 0,  score: 91 },
];

function scoreColor(s: number) {
  return s < 50 ? 'var(--status-critical)' : s < 70 ? 'var(--status-warn)' : s < 85 ? 'var(--status-low)' : 'var(--status-safe)';
}

export default function Analytics() {
  const [range, setRange] = useState<'7d' | '30d' | '90d'>('30d');

  return (
    <div className="v-page">
      <PageHeader
        title="Analytics"
        subtitle="Security trends, review velocity, and finding patterns"
        actions={
          <div style={{ display: 'flex', gap: 4, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 5, padding: 3 }}>
            {(['7d', '30d', '90d'] as const).map(r => (
              <button
                key={r}
                onClick={() => setRange(r)}
                style={{
                  padding: '4px 12px',
                  borderRadius: 4,
                  border: 'none',
                  background: range === r ? 'var(--secondary)' : 'transparent',
                  color: range === r ? 'var(--foreground)' : 'var(--muted-foreground)',
                  fontSize: '0.75rem',
                  fontWeight: range === r ? 500 : 400,
                  cursor: 'pointer',
                  transition: 'all 140ms',
                }}
              >
                {r}
              </button>
            ))}
          </div>
        }
      />

      {/* ── Metrics row ── */}
      <div className="analytics-metric-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
        <MetricCard label="PRs reviewed" value="28" trend={14} spark={[18,21,19,24,20,26,28]} sparkColor="var(--primary)" />
        <MetricCard label="Findings resolved" value="19" trend={22} spark={[8,11,9,14,12,16,19]} sparkColor="var(--status-safe)" />
        <MetricCard label="Avg. review time" value="4.2" unit="h" trend={-18} invert spark={[6.1,5.8,5.2,4.9,4.7,4.4,4.2]} sparkColor="var(--status-warn)" />
        <MetricCard label="Security score" value="71" trend={8} spark={[62,64,63,67,68,70,71]} sparkColor="var(--ai)" />
      </div>

      {/* ── Charts row ── */}
      <div className="analytics-chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, marginBottom: 24 }}>

        {/* Findings over time */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>Findings by severity</div>
            <div style={{ display: 'flex', gap: 12 }}>
              {findingsSeries.map(s => (
                <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div style={{ width: 8, height: 2, background: s.color, borderRadius: 1 }} />
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>{s.name}</span>
                </div>
              ))}
            </div>
          </div>
          <LineChart series={findingsSeries} labels={WEEKS} height={150} />
        </div>

        {/* Severity distribution */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, padding: '18px 20px' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)', marginBottom: 16 }}>
            Distribution
          </div>
          <BarChart data={severityDist} />

          <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-foreground)', marginBottom: 8 }}>
              Total open
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '2rem', fontWeight: 600, color: 'var(--foreground)', lineHeight: 1 }}>
              25
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted-foreground)', marginTop: 3 }}>
              ↓ 4 from last period
            </div>
          </div>
        </div>
      </div>

      {/* ── Repository breakdown table ── */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
        <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)' }}>Repository breakdown</span>
        </div>
        <div className="table-scroll">
        <table className="v-table">
          <thead>
            <tr>
              <th>Repository</th>
              <th>PRs reviewed</th>
              <th>Findings</th>
              <th>Resolved</th>
              <th>Security score</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {repoActivity.map(r => (
              <tr key={r.repo}>
                <td>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: 'var(--foreground)' }}>
                    {r.repo}
                  </span>
                </td>
                <td>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>{r.prs}</span>
                </td>
                <td>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem', color: r.findings > 0 ? 'var(--status-critical)' : 'var(--status-safe)' }}>
                    {r.findings}
                  </span>
                </td>
                <td>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem', color: 'var(--status-safe)' }}>
                    {r.resolved}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 48, height: 3, background: 'var(--secondary)', borderRadius: 1, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${r.score}%`, background: scoreColor(r.score), borderRadius: 1 }} />
                    </div>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem', color: scoreColor(r.score) }}>
                      {r.score}
                    </span>
                  </div>
                </td>
                <td>
                  <Trend value={r.score > 60 ? 8 : -12} invert />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>

      {/* ── Review velocity heatmap concept ── */}
      <div style={{ marginTop: 24, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, padding: '18px 20px' }}>
        <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--foreground)', marginBottom: 4 }}>
          Review activity — last 12 weeks
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--muted-foreground)', marginBottom: 14 }}>
          Each cell represents one day. Darker = more reviews completed.
        </div>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {Array.from({ length: 84 }).map((_, i) => {
            const v = Math.random();
            const opacity = v < 0.3 ? 0.06 : v < 0.5 ? 0.18 : v < 0.75 ? 0.38 : 0.7;
            return (
              <div
                key={i}
                title={`${Math.round(v * 8)} reviews`}
                style={{
                  width: 10, height: 10,
                  borderRadius: 2,
                  background: `rgba(71, 88, 250, ${opacity})`,
                  border: '1px solid var(--border)',
                }}
              />
            );
          })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10 }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--muted-foreground)' }}>Less</span>
          {[0.06, 0.18, 0.38, 0.7].map(o => (
            <div key={o} style={{ width: 10, height: 10, borderRadius: 2, background: `rgba(71,88,250,${o})`, border: '1px solid var(--border)' }} />
          ))}
          <span style={{ fontSize: '0.72rem', color: 'var(--muted-foreground)' }}>More</span>
        </div>
      </div>
    </div>
  );
}
