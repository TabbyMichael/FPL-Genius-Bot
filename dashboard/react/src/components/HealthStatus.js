import React, { useState, useEffect } from 'react';
import { fetchHealthStatus } from '../services/api';

const HealthStatus = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetchHealthStatus();
        setHealth(response.data);
      } catch (err) {
        setError('Failed to fetch health status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading health status...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  const isHealthy = health?.status === 'healthy';

  return (
    <div>
      <h1>Health Status</h1>
      
      <div className={`dashboard-card ${isHealthy ? 'success' : 'error'}`}>
        <h2>System Status</h2>
        <p><strong>Status:</strong> {health?.status?.toUpperCase()}</p>
      </div>

      <div className="dashboard-card">
        <h2>Component Status</h2>
        <div className="metric-grid">
          {health?.details && Object.entries(health.details).map(([component, isHealthy]) => (
            <div key={component} className="metric-card">
              <div className="metric-label">{component}</div>
              <div className={`metric-value ${isHealthy ? 'success' : 'error'}`}>
                {isHealthy ? '✅ Healthy' : '❌ Unhealthy'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HealthStatus;