import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import Overview from './components/Overview';
import PerformanceHistory from './components/PerformanceHistory';
import Predictions from './components/Predictions';
import TransferHistory from './components/TransferHistory';
import HealthStatus from './components/HealthStatus';

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
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;