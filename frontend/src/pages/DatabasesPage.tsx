import { FormEvent, useEffect, useMemo, useState } from 'react';
import useApi from '../hooks/useApi';
import { DatabaseStats, ManagedDatabase } from '../types/api';
import DataTable from '../components/DataTable';
import PageHeader from '../components/PageHeader';
import StatsCard from '../components/StatsCard';
import MapPreview from '../components/MapPreview';

const DatabasesPage = () => {
  const api = useApi();
  const [databases, setDatabases] = useState<ManagedDatabase[]>([]);
  const [stats, setStats] = useState<Record<string, DatabaseStats>>({});
  const [form, setForm] = useState({ name: '', display_name: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'idle' | 'success' | 'error'; text: string }>({
    type: 'idle',
    text: ''
  });

  const loadDatabases = async () => {
    const dbs = await api.get<ManagedDatabase[]>('/databases');
    setDatabases(dbs);
    await Promise.all(
      dbs.map(async (db) => {
        const stat = await api.get<DatabaseStats>(`/databases/${db.name}/stats`);
        setStats((current) => ({ ...current, [db.name]: stat }));
      })
    );
  };

  useEffect(() => {
    loadDatabases().catch((error) => console.error(error));
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setFeedback({ type: 'idle', text: '' });
    try {
      await api.post<ManagedDatabase>('/databases', {
        name: form.name,
        display_name: form.display_name || undefined
      });
      setForm({ name: '', display_name: '' });
      setFeedback({ type: 'success', text: `Database "${form.name}" created.` });
      await loadDatabases();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to create database.';
      setFeedback({ type: 'error', text: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalSize = useMemo(() =>
    Object.values(stats).reduce((acc, current) => acc + (current.size_bytes || 0), 0),
  [stats]);

  return (
    <div>
      <PageHeader title="Managed Databases" subtitle="Create, drop, and inspect PostGIS databases" actions={null} />
      <div className="grid two">
        <form className="card" onSubmit={onSubmit}>
          <h3>Create database</h3>
          <label>
            <div>Name</div>
            <input
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              required
              pattern="[a-z0-9_]+"
              placeholder="osm_europe"
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem', marginBottom: '0.8rem' }}
            />
          </label>
          <label>
            <div>Display name (optional)</div>
            <input
              value={form.display_name}
              onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))}
              placeholder="Europe"
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem', marginBottom: '0.8rem' }}
            />
          </label>
          <button type="submit" className="btn" disabled={isSubmitting}>
            Create
          </button>
          {feedback.type !== 'idle' && (
            <div
              style={{
                marginTop: '0.75rem',
                color: feedback.type === 'error' ? '#dc2626' : '#16a34a'
              }}
            >
              {feedback.text}
            </div>
          )}
        </form>
        <div className="grid three">
          <StatsCard label="Total databases" value={databases.length} />
          <StatsCard label="Total size" value={`${(totalSize / (1024 * 1024)).toFixed(2)} MiB`} />
          <StatsCard label="Latest refresh" value={new Date().toLocaleTimeString()} />
        </div>
      </div>
      <DataTable
        data={databases}
        columns={[
          { header: 'Name', accessor: (db) => db.name },
          { header: 'Display name', accessor: (db) => db.display_name || '—' },
          {
            header: 'Size',
            accessor: (db) => {
              const stat = stats[db.name];
              return stat ? `${(stat.size_bytes / (1024 * 1024)).toFixed(2)} MiB` : '—';
            }
          },
          {
            header: 'Tables',
            accessor: (db) => {
              const stat = stats[db.name];
              return stat ? stat.table_count : '—';
            }
          }
        ]}
      />
      <div className="card">
        <h3>Map preview</h3>
        <p style={{ color: '#64748b' }}>Leaflet preview using the placeholder tiles endpoint.</p>
        <MapPreview />
      </div>
    </div>
  );
};

export default DatabasesPage;
