type StatsCardProps = {
  label: string;
  value: string | number;
  hint?: string;
};

const StatsCard = ({ label, value, hint }: StatsCardProps) => (
  <div className="card">
    <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: '#64748b', letterSpacing: '0.08em' }}>{label}</div>
    <div style={{ fontSize: '1.6rem', fontWeight: 700, marginTop: '0.5rem' }}>{value}</div>
    {hint && <div style={{ marginTop: '0.5rem', color: '#94a3b8' }}>{hint}</div>}
  </div>
);

export default StatsCard;
