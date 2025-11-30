import React, { useState, useEffect } from 'react';
import { fetchPerformanceHistory } from '../services/api';
import PerformanceHistoryTable from './PerformanceHistoryTable';

const PerformanceHistory = () => {
  const [performances, setPerformances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetchPerformanceHistory(11);
        setPerformances(response.data);
      } catch (err) {
        setError('Failed to fetch performance history');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading performance history...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div>
      <h1>Performance History</h1>
      
      <PerformanceHistoryTable performances={performances} />
    </div>
  );

};

export default PerformanceHistory;