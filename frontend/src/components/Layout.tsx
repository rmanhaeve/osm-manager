import { NavLink } from 'react-router-dom';
import React from 'react';

const menuItems = [
  { path: '/databases', label: 'Databases' },
  { path: '/imports', label: 'Imports' },
  { path: '/replication', label: 'Replication' },
  { path: '/jobs', label: 'Jobs' },
  { path: '/settings', label: 'Settings' }
];

type LayoutProps = {
  children: React.ReactNode;
};

const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <h1 style={{ margin: '0 0 1.5rem', fontSize: '1.4rem', fontWeight: 700 }}>OSM Manager</h1>
        <nav>
          {menuItems.map((item) => (
            <NavLink key={item.path} to={item.path} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
};

export default Layout;
