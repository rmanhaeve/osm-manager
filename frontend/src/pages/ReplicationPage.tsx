import { FormEvent, useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import useApi from '../hooks/useApi';
import { ManagedDatabase, ReplicationConfig } from '../types/api';

const DEFAULT_CONFIG = {
  target_db: '',
  base_url: '',
  interval_minutes: 5,
  dry_run: false,
  catch_up: false
};

const ReplicationPage = () => {
  const api = useApi();
  const [configs, setConfigs] = useState<ReplicationConfig[]>([]);
  const [form, setForm] = useState(DEFAULT_CONFIG);
  const [databases, setDatabases] = useState<ManagedDatabase[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const [cfgs, dbs] = await Promise.all([
      api.get<ReplicationConfig[]>('/replication/config'),
      api.get<ManagedDatabase[]>('/databases')
    ]);
    setConfigs(cfgs);
    setDatabases(dbs);
  };

  useEffect(() => {
    load().catch((error) => console.error(error));
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await api.post('/replication/config', {
      ...form,
      interval_minutes: Number(form.interval_minutes)
    });
    setMessage('Replication settings saved.');
    await load();
  };

  const trigger = async (targetDb: string) => {
    await api.post('/replication/update', { target_db: targetDb });
    setMessage(`Replication job queued for ${targetDb}`);
  };

  return (
    <div>
      <PageHeader title="Replication" subtitle="Manage OSM diff catch-up and schedules" />
      <form className="card" onSubmit={onSubmit}>
        <div className="grid two">
          <label>
            <div>Target database</div>
            <select
              required
              value={form.target_db}
              onChange={(event) => setForm((current) => ({ ...current, target_db: event.target.value }))}
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            >
              <option value="" disabled>
                Select database
              </option>
              {databases.map((db) => (
                <option key={db.name} value={db.name}>
                  {db.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <div>Replication interval (minutes)</div>
            <input
              type="number"
              min={1}
              value={form.interval_minutes}
              onChange={(event) => setForm((current) => ({ ...current, interval_minutes: Number(event.target.value) }))}
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            />
          </label>
        </div>
        <label>
          <div>Base URL</div>
          <input
            required
            value={form.base_url}
            onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))}
            placeholder="https://download.geofabrik.de/europe/monaco-updates"
            style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
          />
        </label>
        <div style={{ display: 'flex', gap: '1.5rem', marginTop: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={form.dry_run}
              onChange={(event) => setForm((current) => ({ ...current, dry_run: event.target.checked }))}
            />
            Dry run
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={form.catch_up}
              onChange={(event) => setForm((current) => ({ ...current, catch_up: event.target.checked }))}
            />
            Catch up
          </label>
        </div>
        <button type="submit" className="btn" style={{ marginTop: '1rem' }}>
          Save configuration
        </button>
        {message && <div style={{ marginTop: '0.75rem', color: '#2563eb' }}>{message}</div>}
      </form>

      <DataTable
        data={configs}
        columns={[
          { header: 'Target', accessor: (config) => config.target_db },
          { header: 'Base URL', accessor: (config) => config.base_url },
          { header: 'Interval', accessor: (config) => `${config.interval_minutes} min` },
          {
            header: 'Last sequence',
            accessor: (config) => config.last_sequence_number ?? '—'
          },
          {
            header: 'Actions',
            accessor: (config) => (
              <button type="button" className="btn" onClick={() => trigger(config.target_db)}>
                Run update
              </button>
            )
          }
        ]}
      />
    </div>
  );
};

export default ReplicationPage;
