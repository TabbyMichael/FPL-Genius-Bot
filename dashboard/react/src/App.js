import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import Overview from './components/Overview';
import PerformanceHistory from './components/PerformanceHistory';
import Predictions from './components/Predictions';
import TransferHistory from './components/TransferHistory';
import HealthStatus from './components/HealthStatus';
import Logs from './components/Logs';
import FeatureImportance from './components/FeatureImportance';
import AdminPanel from './components/AdminPanel';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>⚽ FPL Bot Dashboard</h1>
          <nav>
            <ul>
              <li><Link to="/">Overview</Link></li>
              <li><Link to="/performance">Performance History</Link></li>
              <li><Link to="/predictions">Predictions</Link></li>
              <li><Link to="/transfers">Transfer History</Link></li>
              <li><Link to="/health">Health Status</Link></li>
              <li><Link to="/logs">Logs</Link></li>
              <li><Link to="/ml-insights">ML Insights</Link></li>
              <li><Link to="/admin">Admin</Link></li>
            </ul>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/performance" element={<PerformanceHistory />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/transfers" element={<TransferHistory />} />
            <Route path="/health" element={<HealthStatus />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/ml-insights" element={<FeatureImportance />} />
            <Route path="/admin" element={<AdminPanel />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;