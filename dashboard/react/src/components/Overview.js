import React, { useState, useEffect } from 'react';
import { fetchAnalyticsSummary, fetchTeamInfo } from '../services/api';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const Overview = () => {
  const [summary, setSummary] = useState(null);
  const [teamInfo, setTeamInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [summaryResponse, teamResponse] = await Promise.all([
          fetchAnalyticsSummary(),
          fetchTeamInfo()
        ]);
        setSummary(summaryResponse.data);
        setTeamInfo(teamResponse.data);
      } catch (err) {
        setError('Failed to fetch overview data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading overview data...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  const chartData = {
    labels: ['Predictions', 'Performances', 'Transfers'],
    datasets: [
      {
        label: 'Total Count',
        data: [
          summary?.total_predictions || 0,
          summary?.total_performances || 0,
          summary?.total_transfers || 0
        ],
        backgroundColor: [
          'rgba(54, 162, 235, 0.6)',
          'rgba(75, 192, 192, 0.6)',
          'rgba(153, 102, 255, 0.6)'
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)'
        ],
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'FPL Bot Analytics Summary',
      },
    },
  };

  return (
    <div>
      <h1>Dashboard Overview</h1>
      
      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">Total Predictions</div>
          <div className="metric-value">{summary?.total_predictions || 0}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Total Performances</div>
          <div className="metric-value">{summary?.total_performances || 0}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Total Transfers</div>
          <div className="metric-value">{summary?.total_transfers || 0}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Latest Gameweek</div>
          <div className="metric-value">{summary?.latest_gameweek || 0}</div>
        </div>
      </div>

      <div className="dashboard-card">
        <h2>Analytics Summary</h2>
        <div className="chart-container">
          <Bar data={chartData} options={chartOptions} />
        </div>
      </div>

      <div className="dashboard-card">
        <h2>Team Information</h2>
        <p><strong>Team ID:</strong> {teamInfo?.team_id || 'Not configured'}</p>
        <p><strong>Status:</strong> {teamInfo?.status || 'Unknown'}</p>
      </div>
    </div>
  );
};

export default Overview;