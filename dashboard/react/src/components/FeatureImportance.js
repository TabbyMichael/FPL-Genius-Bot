import React, { useState, useEffect } from 'react';
import { fetchFeatureImportance } from '../services/api';
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

const FeatureImportance = () => {
  const [importanceData, setImportanceData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const getImportance = async () => {
      try {
        const response = await fetchFeatureImportance();
        setImportanceData(response.data);
      } catch (err) {
        setError('Failed to fetch feature importance. Is the model trained?');
        console.error(err);
      }
    };
    getImportance();
  }, []);

  const chartData = {
    labels: importanceData ? Object.keys(importanceData) : [],
    datasets: [
      {
        label: 'Feature Importance',
        data: importanceData ? Object.values(importanceData) : [],
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  };

  const options = {
    indexAxis: 'y',
    elements: {
      bar: {
        borderWidth: 2,
      },
    },
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'ML Model Feature Importance',
      },
    },
  };

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!importanceData) {
    return <div>Loading feature importance...</div>;
  }

  return (
    <div className="feature-importance-container">
      <h2>ML Model Insights</h2>
      <Bar data={chartData} options={options} />
    </div>
  );
};

export default FeatureImportance;
