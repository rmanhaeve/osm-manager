type StatusBadgeProps = {
  status: string;
};

const colors: Record<string, string> = {
  success: '#16a34a',
  running: '#2563eb',
  pending: '#f59e0b',
  failed: '#dc2626',
  cancelled: '#64748b'
};

const StatusBadge = ({ status }: StatusBadgeProps) => {
  const color = colors[status] || '#334155';
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.25rem 0.6rem',
        borderRadius: '999px',
        fontSize: '0.8rem',
        fontWeight: 600,
        background: color + '22',
        color
      }}
    >
      <span
        style={{
          width: '0.55rem',
          height: '0.55rem',
          borderRadius: '999px',
          background: color
        }}
      />
      {status}
    </span>
  );
};

export default StatusBadge;
