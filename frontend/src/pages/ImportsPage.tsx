import { FormEvent, useEffect, useMemo, useState } from 'react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useApi from '../hooks/useApi';
import { GEOFABRIK_DATA, GeofabrikEntry } from '../data/geofabrik';
import { Job, ManagedDatabase } from '../types/api';

const DEFAULT_FORM = {
  target_db: '',
  mode: 'create',
  pbf_path: '',
  pbf_url: '',
  slim: true,
  hstore: true,
  cache_mb: 2000,
  number_processes: 4,
  preset_pbf: '',
  style_definition: ''
};

const ImportsPage = () => {
  const api = useApi();
  const [form, setForm] = useState(DEFAULT_FORM);
  const [databases, setDatabases] = useState<ManagedDatabase[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const geofabrikGroups = useMemo(() => {
    const rootEntries = GEOFABRIK_DATA.filter((entry) => !entry.parent).sort((a, b) =>
      a.label.localeCompare(b.label)
    );
    const roots = new Map(rootEntries.map((entry) => [entry.id, entry]));

    const groups = new Map<string, GeofabrikEntry[]>();
    GEOFABRIK_DATA.forEach((entry) => {
      if (!entry.parent) {
        return;
      }
      const root = roots.get(entry.parent);
      if (!root) {
        return;
      }
      if (!groups.has(root.label)) {
        groups.set(root.label, []);
      }
      groups.get(root.label)!.push(entry);
    });

    const grouped = Array.from(groups.entries())
      .map(([label, items]) => ({
        label,
        items: items.sort((a, b) => a.label.localeCompare(b.label))
      }))
      .sort((a, b) => a.label.localeCompare(b.label));

    if (rootEntries.length) {
      grouped.unshift({ label: 'Continents', items: rootEntries });
    }

    return grouped;
  }, []);

  const refresh = async () => {
    const [dbs, jobPayload] = await Promise.all([
      api.get<ManagedDatabase[]>('/databases'),
      api.get<{ items: Job[]; total: number }>('/jobs')
    ]);
    setDatabases(dbs);
    setJobs(jobPayload.items.filter((job) => job.type === 'import'));
  };

  useEffect(() => {
    refresh().catch((error) => console.error(error));
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      refresh().catch((error) => console.error(error));
    }, 5000);
    return () => window.clearInterval(interval);
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.pbf_path && !form.pbf_url) {
      setMessage('Provide a local path or a remote .pbf URL.');
      return;
    }
    await api.post('/imports', {
      target_db: form.target_db,
      mode: form.mode,
      pbf_path: form.pbf_path || undefined,
      pbf_url: form.pbf_url || undefined,
      slim: form.slim,
      hstore: form.hstore,
      cache_mb: form.cache_mb,
      number_processes: form.number_processes,
      style_definition: form.style_definition || undefined
    });
    setMessage('Import queued successfully.');
    setForm((current) => ({ ...current, pbf_path: '', pbf_url: '', preset_pbf: '', style_definition: '' }));
    await refresh();
  };

  return (
    <div>
      <PageHeader
        title="OSM Imports"
        subtitle="Kick off new osm2pgsql imports and monitor progress"
        actions={null}
      />
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
            <div>Mode</div>
            <select
              value={form.mode}
              onChange={(event) => setForm((current) => ({ ...current, mode: event.target.value }))}
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            >
              <option value="create">Create</option>
              <option value="append">Append</option>
            </select>
          </label>
        </div>
        <div className="grid two">
          <label>
            <div>Local PBF path</div>
            <input
              value={form.pbf_path}
              onChange={(event) => setForm((current) => ({ ...current, pbf_path: event.target.value }))}
              placeholder="/data/pbf/europe-latest.osm.pbf"
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            />
          </label>
          <label>
            <div>Remote PBF URL</div>
            <input
              value={form.pbf_url}
              onChange={(event) =>
                setForm((current) => ({ ...current, pbf_url: event.target.value, preset_pbf: '' }))
              }
              placeholder="https://download.geofabrik.de/europe/monaco-latest.osm.pbf"
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            />
            <select
              value={form.preset_pbf}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  preset_pbf: event.target.value,
                  pbf_url: event.target.value || current.pbf_url
                }))
              }
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.6rem' }}
            >
              <option value="">Select a Geofabrik preset</option>
              {geofabrikGroups.map((group) => (
                <optgroup key={group.label} label={group.label}>
                  {group.items.map((entry) => (
                    <option key={entry.url} value={entry.url}>
                      {entry.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
        </div>
        <div className="grid three">
          <label>
            <div>Cache (MB)</div>
            <input
              type="number"
              min={64}
              max={16000}
              value={form.cache_mb}
              onChange={(event) => setForm((current) => ({ ...current, cache_mb: Number(event.target.value) }))}
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            />
          </label>
          <label>
            <div>Parallel jobs</div>
            <input
              type="number"
              min={1}
              max={16}
              value={form.number_processes}
              onChange={(event) =>
                setForm((current) => ({ ...current, number_processes: Number(event.target.value) }))
              }
              style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
            />
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1.8rem' }}>
            <input
              type="checkbox"
              checked={form.slim}
              onChange={(event) => setForm((current) => ({ ...current, slim: event.target.checked }))}
            />
            Slim mode
          </label>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            checked={form.hstore}
            onChange={(event) => setForm((current) => ({ ...current, hstore: event.target.checked }))}
          />
          Enable hstore
        </label>
        <label>
          <div>Custom table definition</div>
          <textarea
            value={form.style_definition}
            onChange={(event) => setForm((current) => ({ ...current, style_definition: event.target.value }))}
            placeholder="# Paste osm2pgsql style definitions here"
            style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem', minHeight: '6rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco' }}
          />
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
            Optional inline osm2pgsql style contents defining tables/columns.
          </span>
        </label>
        <button type="submit" className="btn" style={{ marginTop: '1rem' }}>
          Start import
        </button>
        {message && <div style={{ marginTop: '0.75rem', color: '#2563eb' }}>{message}</div>}
      </form>

      <DataTable
        data={jobs}
        columns={[
          { header: 'Job ID', accessor: (job) => job.id.slice(0, 8) },
          { header: 'Target', accessor: (job) => job.target_db || '—' },
          {
            header: 'Status',
            accessor: (job) => {
              const status = job.status === 'pending' && job.started_at ? 'running' : job.status;
              return <StatusBadge status={status} />;
            }
          },
          {
            header: 'Started',
            accessor: (job) => (job.started_at ? new Date(job.started_at).toLocaleString() : '—')
          },
          {
            header: 'Finished',
            accessor: (job) => (job.finished_at ? new Date(job.finished_at).toLocaleString() : '—')
          }
        ]}
      />
    </div>
  );
};

export default ImportsPage;
