import { useEffect, useRef, useState } from 'react';

type LogViewerProps = {
  lines: { ts: string; line: string }[];
  title?: string;
  maxHeight?: string;
};

type LogLevel = 'error' | 'warn' | 'info' | 'debug' | 'progress';

const detectLogLevel = (line: string): LogLevel => {
  const lower = line.toLowerCase();
  if (lower.includes('error') || lower.includes('exception') || lower.includes('failed') || lower.includes('traceback')) {
    return 'error';
  }
  if (lower.includes('warn')) {
    return 'warn';
  }
  if (/\d+%|processing|importing|nodes|ways|relations/.test(lower)) {
    return 'progress';
  }
  if (lower.includes('debug')) {
    return 'debug';
  }
  return 'info';
};

const levelColors: Record<LogLevel, string> = {
  error: '#f87171',
  warn: '#fbbf24',
  info: '#e2e8f0',
  debug: '#64748b',
  progress: '#34d399'
};

const LogViewer = ({ lines, title, maxHeight = '400px' }: LogViewerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('');
  const [showErrors, setShowErrors] = useState(false);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  const filteredLines = lines.filter((line) => {
    const matchesFilter = !filter || line.line.toLowerCase().includes(filter.toLowerCase());
    const matchesErrorFilter = !showErrors || detectLogLevel(line.line) === 'error';
    return matchesFilter && matchesErrorFilter;
  });

  const errorCount = lines.filter((line) => detectLogLevel(line.line) === 'error').length;

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1rem',
          background: '#1e293b',
          borderBottom: '1px solid #334155',
          gap: '0.75rem',
          flexWrap: 'wrap'
        }}
      >
        <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '0.9rem' }}>
          {title || 'Logs'} ({filteredLines.length})
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="Filter..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              padding: '0.35rem 0.6rem',
              fontSize: '0.8rem',
              borderRadius: '0.35rem',
              border: '1px solid #475569',
              background: '#0f172a',
              color: '#e2e8f0',
              width: '120px'
            }}
          />
          <button
            type="button"
            onClick={() => setShowErrors(!showErrors)}
            style={{
              padding: '0.35rem 0.6rem',
              fontSize: '0.75rem',
              borderRadius: '0.35rem',
              border: 'none',
              background: showErrors ? '#dc2626' : '#475569',
              color: 'white',
              cursor: 'pointer'
            }}
            title="Show errors only"
          >
            🔴 {errorCount}
          </button>
          <button
            type="button"
            onClick={() => {
              setAutoScroll(true);
              if (containerRef.current) {
                containerRef.current.scrollTop = containerRef.current.scrollHeight;
              }
            }}
            style={{
              padding: '0.35rem 0.6rem',
              fontSize: '0.75rem',
              borderRadius: '0.35rem',
              border: 'none',
              background: autoScroll ? '#16a34a' : '#475569',
              color: 'white',
              cursor: 'pointer'
            }}
            title="Auto-scroll"
          >
            ↓
          </button>
        </div>
      </div>

      {/* Log content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          maxHeight,
          overflowY: 'auto',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco',
          fontSize: '0.78rem',
          lineHeight: 1.5,
          background: '#0f172a',
          color: '#e2e8f0',
          padding: '0.75rem 1rem'
        }}
      >
        {filteredLines.length === 0 && (
          <div style={{ opacity: 0.5 }}>
            {lines.length === 0 ? 'No logs yet. Select a job to view logs.' : 'No matching logs.'}
          </div>
        )}
        {filteredLines.map((line, idx) => {
          const level = detectLogLevel(line.line);
          return (
            <div
              key={`${line.ts}-${idx}`}
              style={{
                marginBottom: '0.25rem',
                color: levelColors[level],
                background: level === 'error' ? 'rgba(248, 113, 113, 0.1)' : undefined,
                padding: level === 'error' ? '0.2rem 0.4rem' : undefined,
                borderRadius: level === 'error' ? '0.25rem' : undefined
              }}
            >
              <span style={{ opacity: 0.5, marginRight: '0.75rem', fontSize: '0.72rem' }}>
                {line.ts}
              </span>
              <span>{line.line}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LogViewer;
