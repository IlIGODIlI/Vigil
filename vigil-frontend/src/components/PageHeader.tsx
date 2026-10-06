interface Props {
  title: string;
  titleHi?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumb?: string;
}

export default function PageHeader({ title, subtitle, actions, breadcrumb }: Props) {
  return (
    <div className="page-header" style={{
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: 16,
      marginBottom: 28,
      paddingBottom: 20,
      borderBottom: '1px solid var(--border)',
    }}>
      <div className="page-header-copy">
        {breadcrumb && (
          <div style={{
            fontSize: '0.72rem',
            color: 'var(--muted-foreground)',
            marginBottom: 5,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span>Vigil</span>
            <span style={{ opacity: 0.4 }}>›</span>
            <span>{breadcrumb}</span>
          </div>
        )}
        <h1 className="page-title" style={{
          fontSize: '1.75rem',
          fontWeight: 650,
          letterSpacing: '-0.03em',
          color: 'var(--foreground)',
          margin: '0 0 6px',
          lineHeight: 1.15,
        }}>
          {title}
        </h1>
        {subtitle && (
          <p className="page-subtitle" style={{
            fontSize: '0.82rem',
            color: 'var(--secondary-foreground)',
            margin: 0,
            lineHeight: 1.5,
          }}>
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div className="page-header-actions" style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
          {actions}
        </div>
      )}
    </div>
  );
}
