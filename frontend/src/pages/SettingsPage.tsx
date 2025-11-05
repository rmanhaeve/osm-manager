import PageHeader from '../components/PageHeader';

const SettingsPage = () => {
  const envInfo = {
    apiBase: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    adminTokenConfigured: Boolean(import.meta.env.VITE_ADMIN_TOKEN)
  };

  return (
    <div>
      <PageHeader title="Settings" subtitle="Runtime configuration and environment" />
      <div className="card">
        <h3>Environment</h3>
        <p>API base URL: {envInfo.apiBase}</p>
        <p>Admin token configured: {envInfo.adminTokenConfigured ? 'Yes' : 'No'}</p>
        <p>App version: {import.meta.env.MODE}</p>
      </div>
      <div className="card">
        <h3>Worker limits</h3>
        <p>Adjust concurrency via environment variables:</p>
        <ul>
          <li><code>OSM_MANAGER__WORKER__MAX_CONCURRENT_IMPORTS</code></li>
          <li><code>OSM_MANAGER__WORKER__MAX_CONCURRENT_REPLICATIONS</code></li>
          <li><code>OSM_MANAGER__WORKER__PARALLEL_WORKERS</code></li>
        </ul>
      </div>
    </div>
  );
};

export default SettingsPage;
