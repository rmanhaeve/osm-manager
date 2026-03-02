import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import useApi from '../hooks/useApi';
import { DatabaseBounds, DatabaseStats, ManagedDatabase } from '../types/api';
import DataTable from '../components/DataTable';
import PageHeader from '../components/PageHeader';
import StatsCard from '../components/StatsCard';
import MapPreview, { MapPreviewHandle } from '../components/MapPreview';
import { useToast } from '../components/ToastProvider';

const DatabasesPage = () => {
  const api = useApi();
  const { addToast } = useToast();
  const [databases, setDatabases] = useState<ManagedDatabase[]>([]);
  const [stats, setStats] = useState<Record<string, DatabaseStats>>({});
  const [form, setForm] = useState({ name: '', display_name: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedDb, setSelectedDb] = useState<string | null>(null);
  const mapRef = useRef<MapPreviewHandle | null>(null);

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
    try {
      await api.post<ManagedDatabase>('/databases', {
        name: form.name,
        display_name: form.display_name || undefined
      });
      addToast('success', `Database "${form.name}" created.`);
      setForm({ name: '', display_name: '' });
      await loadDatabases();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to create database.';
      addToast('error', message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const deleteDatabase = async (name: string) => {
    if (!window.confirm(`Delete database "${name}"? This cannot be undone.`)) {
      return;
    }
    try {
      await api.del(`/databases/${name}`);
      addToast('success', `Database "${name}" deleted.`);
      await loadDatabases();
      setSelectedDb((current) => (current === name ? null : current));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to delete database.';
      addToast('error', message);
    }
  };

  const totalSize = useMemo(() =>
    Object.values(stats).reduce((acc, current) => acc + (current.size_bytes || 0), 0),
  [stats]);
  const connectionInfo = useMemo(() => {
    const url = new URL(window.location.origin);
    const host = url.hostname || 'localhost';
    const port = import.meta.env.VITE_POSTGRES_PORT || '5433';
    return { host, port };
  }, []);

  const showBounds = async (dbName: string) => {
    const record = databases.find((db) => db.name === dbName);
    if (
      record &&
      record.min_lat !== undefined &&
      record.min_lon !== undefined &&
      record.max_lat !== undefined &&
      record.max_lon !== undefined
    ) {
      mapRef.current?.showBounds([
        [record.min_lat, record.min_lon],
        [record.max_lat, record.max_lon]
      ]);
      setSelectedDb(dbName);
      return;
    }

    addToast('info', `Fetching map bounds for "${dbName}"...`);
    try {
      const bounds = await api.get<DatabaseBounds>(`/databases/${dbName}/bounds`);
      mapRef.current?.showBounds([
        [bounds.min_lat, bounds.min_lon],
        [bounds.max_lat, bounds.max_lon]
      ]);
      setSelectedDb(dbName);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to fetch bounds for this database.';
      addToast('error', message);
    }
  };

  useEffect(() => {
    if (databases.length && !selectedDb) {
      showBounds(databases[0].name).catch((error) => console.error(error));
    }
  }, [databases, selectedDb]);

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
        </form>
        <div className="grid two">
          <StatsCard label="Total databases" value={databases.length} />
          <StatsCard label="Total size" value={`${(totalSize / (1024 * 1024)).toFixed(2)} MiB`} />
        </div>
      </div>
      <DataTable
        data={databases}
        columns={[
          {
            header: 'Name',
            accessor: (db) => (
              <button
                type="button"
                onClick={() => showBounds(db.name)}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  color: '#2563eb',
                  cursor: 'pointer',
                  fontWeight: selectedDb === db.name ? 700 : 500
                }}
              >
                {db.name}
              </button>
            )
          },
          { header: 'Display name', accessor: (db) => db.display_name || '—' },
          {
            header: 'Size',
            accessor: (db) => {
              const stat = stats[db.name];
              return stat ? `${(stat.size_bytes / (1024 * 1024)).toFixed(2)} MiB` : '—';
            }
          },
          {
            header: 'Connection URL',
            accessor: (db) => {
              let username = 'app_user';
              let password = 'app_password';
              let databaseName = `osm_${db.name}`;
              try {
                const dsnUrl = new URL(db.dsn.replace('+psycopg', ''));
                username = dsnUrl.username || username;
                password = dsnUrl.password || password;
                const path = dsnUrl.pathname.replace('/', '');
                if (path) {
                  databaseName = path;
                }
              } catch (error) {
                // fallback to defaults
              }
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  <code style={{ fontSize: '0.82rem' }}>
                    {`postgresql://${username}:${password}@${connectionInfo.host}:${connectionInfo.port}/${databaseName}`}
                  </code>
                  <code style={{ fontSize: '0.82rem' }}>
                    {`host=${connectionInfo.host} port=${connectionInfo.port} dbname=${databaseName} user=${username} password=${password}`}
                  </code>
                </div>
              );
            }
          },
          {
            header: 'Tables',
            accessor: (db) => {
              const stat = stats[db.name];
              return stat ? stat.table_count : '—';
            }
          },
          {
            header: 'Actions',
            accessor: (db) => (
              <button
                type="button"
                className="btn btn-small-danger"
                onClick={() => deleteDatabase(db.name)}
                title="Delete database"
                aria-label={`Delete database ${db.name}`}
              >
                ×
              </button>
            )
          }
        ]}
      />
      <div className="card">
        <h3>Map preview</h3>
        <p style={{ color: '#64748b' }}>Leaflet preview using the placeholder tiles endpoint.</p>
        <MapPreview ref={mapRef} />
      </div>
      <div className="card">
        <h3>Table definition</h3>
        <textarea
          readOnly
          value={
            selectedDb
              ? databases.find((db) => db.name === selectedDb)?.style_definition || 'No inline table definition stored.'
              : 'Select a database above to view the stored table definition.'
          }
          style={{
            width: '100%',
            minHeight: '10rem',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco',
            fontSize: '0.85rem',
            background: '#0f172a',
            color: '#e2e8f0',
            borderRadius: '0.5rem',
            padding: '1rem'
          }}
        />
        <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.75rem' }}>
          Inline styles are captured from the most recent import for this database.
        </p>
      </div>
    </div>
  );
};

export default DatabasesPage;
