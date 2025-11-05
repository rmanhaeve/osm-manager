type LogViewerProps = {
  lines: { ts: string; line: string }[];
};

const LogViewer = ({ lines }: LogViewerProps) => {
  return (
    <div
      className="card"
      style={{
        maxHeight: '320px',
        overflowY: 'auto',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco',
        background: '#0f172a',
        color: '#e2e8f0'
      }}
    >
      {lines.length === 0 && <div>No logs yet.</div>}
      {lines.map((line) => (
        <div key={line.ts} style={{ marginBottom: '0.35rem' }}>
          <span style={{ opacity: 0.6, marginRight: '0.75rem' }}>{line.ts}</span>
          <span>{line.line}</span>
        </div>
      ))}
    </div>
  );
};

export default LogViewer;
