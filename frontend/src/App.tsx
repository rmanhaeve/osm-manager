import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import DatabasesPage from './pages/DatabasesPage';
import ImportsPage from './pages/ImportsPage';
import JobsPage from './pages/JobsPage';
import ReplicationPage from './pages/ReplicationPage';
import SettingsPage from './pages/SettingsPage';

const App = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/databases" replace />} />
        <Route path="/databases" element={<DatabasesPage />} />
        <Route path="/imports" element={<ImportsPage />} />
        <Route path="/replication" element={<ReplicationPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
};

export default App;
