import React, { useState, useEffect } from 'react';
import { fetchSystemLogs } from '../services/api';
import './Logs.css';

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const getLogs = async () => {
      try {
        const response = await fetchSystemLogs(200); // Fetch last 200 lines
        setLogs(response.data.logs || []);
      } catch (err) {
        setError('Failed to fetch logs.');
        console.error(err);
      }
    };
    getLogs();
  }, []);

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="logs-container">
      <h2>System Logs</h2>
      <pre className="logs-content">
        {logs.join('')}
      </pre>
    </div>
  );
};

export default Logs;
