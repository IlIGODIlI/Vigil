import { useMemo, useState } from 'react';
import PageHeader from '../components/PageHeader';

type Range = '7d' | '30d' | '90d';
type Severity = 'critical' | 'high' | 'medium' | 'low';

interface RepositoryActivity {
  repo: string;
  prsReviewed: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  resolved: number;
  awaitingDecision: number;
  recentActivity: string;
}

interface AnalyticsDataset {
  chartLabels: string[];
  repositories: RepositoryActivity[];
  severityHistory: Record<Severity, number[]>;
  resolvedHistory: number[];
  reviewActivity: number[];
  activityUnit: 'day' | 'week';
}

const ANALYTICS_DATA: Record<Range, AnalyticsDataset> = {
  '7d': {
    chartLabels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    repositories: [
      { repo: 'api-gateway', prsReviewed: 4, critical: 1, high: 1, medium: 1, low: 0, resolved: 2, awaitingDecision: 1, recentActivity: '2h ago' },
      { repo: 'auth-service', prsReviewed: 2, critical: 0, high: 0, medium: 1, low: 1, resolved: 1, awaitingDecision: 1, recentActivity: '5h ago' },
      { repo: 'web-frontend', prsReviewed: 3, critical: 0, high: 0, medium: 0, low: 1, resolved: 2, awaitingDecision: 0, recentActivity: '1d ago' },
      { repo: 'data-pipeline', prsReviewed: 1, critical: 0, high: 0, medium: 0, low: 0, resolved: 1, awaitingDecision: 0, recentActivity: '2d ago' },
    ],
    severityHistory: {
      critical: [0, 0, 1, 1, 1, 1, 1],
      high: [0, 1, 1, 1, 1, 1, 1],
      medium: [1, 1, 1, 2, 2, 2, 2],
      low: [0, 1, 1, 1, 2, 2, 2],
    },
    resolvedHistory: [0, 1, 2, 3, 4, 5, 6],
    reviewActivity: [1, 2, 0, 2, 1, 3, 1],
    activityUnit: 'day',
  },
  '30d': {
    chartLabels: ['Day 1', 'Day 8', 'Day 15', 'Day 22', 'Day 30'],
    repositories: [
      { repo: 'api-gateway', prsReviewed: 18, critical: 2, high: 2, medium: 3, low: 2, resolved: 8, awaitingDecision: 2, recentActivity: '2h ago' },
      { repo: 'auth-service', prsReviewed: 11, critical: 0, high: 1, medium: 2, low: 2, resolved: 4, awaitingDecision: 1, recentActivity: '5h ago' },
      { repo: 'web-frontend', prsReviewed: 14, critical: 0, high: 1, medium: 1, low: 1, resolved: 3, awaitingDecision: 1, recentActivity: '1d ago' },
      { repo: 'data-pipeline', prsReviewed: 6, critical: 0, high: 0, medium: 0, low: 0, resolved: 0, awaitingDecision: 0, recentActivity: '3d ago' },
    ],
    severityHistory: {
      critical: [1, 1, 2, 2, 2],
      high: [2, 3, 3, 4, 4],
      medium: [3, 4, 5, 5, 6],
      low: [2, 3, 4, 4, 5],
    },
    resolvedHistory: [5, 8, 11, 13, 15],
    reviewActivity: [1, 2, 1, 0, 3, 2, 1, 2, 1, 3, 0, 2, 1, 2, 3, 1, 2, 2, 1, 3, 2, 1, 2, 2, 1, 2, 1, 2, 2, 1],
    activityUnit: 'day',
  },
  '90d': {
    chartLabels: ['Week 1', 'Week 4', 'Week 8', 'Week 12', 'Week 13'],
    repositories: [
      { repo: 'api-gateway', prsReviewed: 42, critical: 3, high: 4, medium: 6, low: 5, resolved: 17, awaitingDecision: 3, recentActivity: '2h ago' },
      { repo: 'auth-service', prsReviewed: 29, critical: 1, high: 3, medium: 4, low: 4, resolved: 10, awaitingDecision: 2, recentActivity: '5h ago' },
      { repo: 'web-frontend', prsReviewed: 33, critical: 0, high: 2, medium: 3, low: 4, resolved: 9, awaitingDecision: 1, recentActivity: '1d ago' },
      { repo: 'data-pipeline', prsReviewed: 18, critical: 0, high: 0, medium: 1, low: 1, resolved: 4, awaitingDecision: 0, recentActivity: '3d ago' },
    ],
    severityHistory: {
      critical: [2, 3, 3, 4, 4],
      high: [4, 5, 7, 8, 9],
      medium: [8, 10, 11, 13, 14],
      low: [7, 9, 11, 13, 14],
    },
    resolvedHistory: [17, 24, 31, 36, 40],
    reviewActivity: [8, 10, 9, 11, 7, 12, 10, 9, 11, 8, 10, 9, 8],
    activityUnit: 'week',
  },
};

const SEVERITIES: Array<{ key: Severity; label: string; color: string }> = [
  { key: 'critical', label: 'Critical', color: 'var(--status-critical)' },
  { key: 'high', label: 'High', color: 'var(--status-high)' },
  { key: 'medium', label: 'Medium', color: 'var(--status-warn)' },
  { key: 'low', label: 'Low', color: 'var(--status-low)' },
];

function cumulative(values: number[]) {
  let total = 0;
  return values.map(value => {
    total += value;
    return total;
  });
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const width = 200;
  const height = 44;
  const pad = 4;
  const xStep = (width - pad * 2) / Math.max(data.length - 1, 1);
  const points = data.map((value, index) => ({
    x: pad + index * xStep,
    y: height - pad - ((value - min) / range) * (height - pad * 2),
  }));
  const polyline = points.map(point => `${point.x},${point.y}`).join(' ');
  const area = `${points[0].x},${height} ${polyline} ${points[points.length - 1].x},${height}`;
  const gradientId = `metric-${color.replace(/[^a-z0-9]/gi, '')}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${gradientId})`} />
      <polyline points={polyline} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r={2.5} fill={color} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function MetricCard({ label, value, range, spark, color }: {
  label: string;
  value: number;
  range: Range;
  spark: number[];
  color: string;
}) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 6, padding: '18px 20px' }}>
      <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted-foreground)', marginBottom: 10 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.8rem', fontWeight: 600, color: 'var(--foreground)', lineHeight: 1 }}>
          {value}
        </span>
        <span style={{ color: 'var(--muted-foreground)', fontSize: '0.7rem' }}>{range}</span>
      </div>
      <Sparkline data={spark} color={color} />
    </div>
  );
}

function BarChart({ data }: { data: Array<{ label: string; value: number; color: string }> }) {
  const max = Math.max(...data.map(item => item.value), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {data.map(({ label, value, color }) => (
        <div key={label}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--secondary-foreground)' }}>{label}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem', fontWeight: 600, color: 'var(--foreground)' }}>{value}</span>
          </div>
          <div style={{ height: 5, background: 'var(--secondary)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(value / max) * 100}%`, background: color, borderRadius: 2, transition: 'width 600ms ease' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function LineChart({ series, labels }: {
  series: Array<{ name: string; data: number[]; color: string }>;
  labels: string[];
}) {
  const width = 640;
  const height = 220;
  const padLeft = 34;
  const padRight = 10;
  const padY = 12;
  const max = Math.max(...series.flatMap(item => item.data), 1);
  const xStep = (width - padLeft - padRight) / Math.max(labels.length - 1, 1);
  const pointsFor = (data: number[]) => data.map((value, index) => ({
    x: padLeft + index * xStep,
    y: height - padY - (value / max) * (height - padY * 2),
  }));

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none" style={{ display: 'block' }}>
        {[0, 0.25, 0.5, 0.75, 1].map(tick => {
          const y = height - padY - tick * (height - padY * 2);
          return (
            <g key={tick}>
              <line x1={padLeft} y1={y} x2={width - padRight} y2={y} stroke="var(--border)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
              <text x={0} y={y + 3} fill="var(--muted-foreground)" fontSize="10">{Math.round(tick * max)}</text>
            </g>
          );
        })}
        {series.map(item => {
          const points = pointsFor(item.data);
          const polyline = points.map(point => `${point.x},${point.y}`).join(' ');
          const area = `${points[0].x},${height - padY} ${polyline} ${points[points.length - 1].x},${height - padY}`;
          const gradientId = `severity-${item.name.toLowerCase()}`;
          return (
            <g key={item.name}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={item.color} stopOpacity="0.14" />
                  <stop offset="100%" stopColor={item.color} stopOpacity="0" />
                </linearGradient>
              </defs>
              <polygon points={area} fill={`url(#${gradientId})`} />
              <polyline points={polyline} fill="none" stroke={item.color} strokeWidth="1.75" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
            </g>
          );
        })}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 34, marginTop: 7 }}>
        {labels.map(label => (
          <span key={label} style={{ fontSize: '0.7rem', color: 'var(--muted-foreground)', fontFamily: 'JetBrains Mono, monospace' }}>
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Analytics() {
  const [range, setRange] = useState<Range>('30d');
  const dataset = ANALYTICS_DATA[range];

  const analytics = useMemo(() => {
    const prsReviewed = dataset.repositories.reduce((total, repo) => total + repo.prsReviewed, 0);
    const resolved = dataset.repositories.reduce((total, repo) => total + repo.resolved, 0);
    const awaitingDecision = dataset.repositories.reduce((total, repo) => total + repo.awaitingDecision, 0);
    const severityTotals = SEVERITIES.reduce<Record<Severity, number>>((totals, severity) => {
      totals[severity.key] = dataset.repositories.reduce((total, repo) => total + repo[severity.key], 0);
      return totals;
    }, { critical: 0, high: 0, medium: 0, low: 0 });
    const openFindings = Object.values(severityTotals).reduce((total, value) => total + value, 0);
    const severitySeries = SEVERITIES.map(severity => ({
      name: severity.label,
      data: dataset.severityHistory[severity.key],
      color: severity.color,
    }));
    const severityDistribution = SEVERITIES.map(severity => ({
      label: severity.label,
      value: severityTotals[severity.key],
      color: severity.color,
    }));

    return {
      prsReviewed,
      resolved,
      awaitingDecision,
      severityTotals,
      openFindings,
      severitySeries,
      severityDistribution,
    };
  }, [dataset]);

  const findingsHistory = dataset.chartLabels.map((_, index) =>
    SEVERITIES.reduce((total, severity) => total + dataset.severityHistory[severity.key][index], 0),
  );
  const activityMax = Math.max(...dataset.reviewActivity, 1);

  return (
    <div className="v-page">
      <PageHeader
        title="Analytics"
        subtitle="Security trends, PR review activity, and finding patterns"
        actions={
          <div className="analytics-range" aria-label="Analytics time range">
            <span>Range</span>
            {(['7d', '30d', '90d'] as const).map(option => (
              <button
                key={option}
                onClick={() => setRange(option)}
                aria-pressed={range === option}
                className={range === option ? 'active' : ''}
              >
                {option}
              </button>
            ))}
          </div>
        }
      />

      <section className="analytics-section">
        <div className="analytics-section-heading">
          <div>
            <strong>Review Overview</strong>
            <span>PR analysis and finding activity for the selected {range} range</span>
          </div>
        </div>
        <div className="analytics-metric-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
          <MetricCard label="PRs Reviewed" value={analytics.prsReviewed} range={range} spark={cumulative(dataset.reviewActivity)} color="var(--primary)" />
          <MetricCard label="Open Findings" value={analytics.openFindings} range={range} spark={findingsHistory} color="var(--status-warn)" />
          <MetricCard label="Critical Findings" value={analytics.severityTotals.critical} range={range} spark={dataset.severityHistory.critical} color="var(--status-critical)" />
          <MetricCard label="Findings Resolved" value={analytics.resolved} range={range} spark={dataset.resolvedHistory} color="var(--status-safe)" />
        </div>
      </section>

      <section className="analytics-section">
        <div className="analytics-section-heading">
          <div>
            <strong>Security Findings</strong>
            <span>Open findings produced by AI analysis, grouped by severity</span>
          </div>
        </div>
        <div className="analytics-chart-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 20 }}>
          <div className="analytics-card">
            <div className="analytics-card-header">
              <strong>Findings by severity</strong>
              <div className="analytics-legend">
                {analytics.severitySeries.map(series => (
                  <span key={series.name}><i style={{ background: series.color }} />{series.name}</span>
                ))}
              </div>
            </div>
            <LineChart series={analytics.severitySeries} labels={dataset.chartLabels} />
          </div>

          <div className="analytics-card">
            <div className="analytics-card-header"><strong>Current distribution</strong></div>
            <BarChart data={analytics.severityDistribution} />
            <div className="analytics-total">
              <span>Total open</span>
              <strong>{analytics.openFindings}</strong>
              <small>{range} selected range</small>
            </div>
          </div>
        </div>
      </section>

      <section className="analytics-section">
        <div className="analytics-card analytics-table-card">
          <div className="analytics-card-header">
            <div>
              <strong>Repository Breakdown</strong>
              <span>Repository-level PR review and finding activity</span>
            </div>
          </div>
          <div className="table-scroll">
            <table className="v-table">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>PRs Reviewed</th>
                  <th>Open Findings</th>
                  <th>Resolved</th>
                  <th>Awaiting Decision</th>
                  <th>Recent Activity</th>
                </tr>
              </thead>
              <tbody>
                {dataset.repositories.map(repo => {
                  const openFindings = repo.critical + repo.high + repo.medium + repo.low;
                  return (
                    <tr key={repo.repo}>
                      <td><span className="analytics-repo-name">{repo.repo}</span></td>
                      <td><span className="analytics-number">{repo.prsReviewed}</span></td>
                      <td><span className={openFindings > 0 ? 'analytics-number text-critical' : 'analytics-number text-safe'}>{openFindings}</span></td>
                      <td><span className="analytics-number text-safe">{repo.resolved}</span></td>
                      <td><span className="analytics-number">{repo.awaitingDecision}</span></td>
                      <td><span className="text-dim">{repo.recentActivity}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="analytics-section">
        <div className="analytics-card">
          <div className="analytics-card-header">
            <div>
              <strong>Review Activity — {range}</strong>
              <span>Human reviews completed during the selected period</span>
            </div>
            <span className="analytics-awaiting">{analytics.awaitingDecision} PRs awaiting human decision</span>
          </div>
          <div className="analytics-activity-grid">
            {dataset.reviewActivity.map((reviews, index) => {
              const opacity = reviews === 0 ? 0.06 : 0.14 + (reviews / activityMax) * 0.56;
              return (
                <div
                  key={`${range}-${index}`}
                  title={`${reviews} ${reviews === 1 ? 'review' : 'reviews'}`}
                  style={{ background: `rgba(71, 88, 250, ${opacity})` }}
                />
              );
            })}
          </div>
          <div className="analytics-activity-footer">
            <span>Each cell represents one {dataset.activityUnit}</span>
            <div><span>Less</span>{[0.06, 0.18, 0.38, 0.7].map(opacity => <i key={opacity} style={{ background: `rgba(71,88,250,${opacity})` }} />)}<span>More</span></div>
          </div>
        </div>
      </section>
    </div>
  );
}
