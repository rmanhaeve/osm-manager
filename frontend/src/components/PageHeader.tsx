type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
};

const PageHeader = ({ title, subtitle, actions }: PageHeaderProps) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
      <div>
        <h2 style={{ margin: 0 }}>{title}</h2>
        {subtitle && <p style={{ margin: '0.4rem 0 0', color: '#64748b' }}>{subtitle}</p>}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
};

export default PageHeader;
