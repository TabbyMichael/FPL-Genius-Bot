import React, { useState, useEffect } from 'react';
import { fetchLatestPredictions } from '../services/api';
import { Bar, Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const Predictions = () => {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetchLatestPredictions(100);
        setPredictions(response.data);
      } catch (err) {
        setError('Failed to fetch predictions');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading predictions...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  // Prepare data for charts
  const histogramData = {
    labels: predictions.slice(0, 20).map(p => p.player_name),
    datasets: [
      {
        label: 'Predicted Points',
        data: predictions.slice(0, 20).map(p => p.predicted_points),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  };

  const histogramOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Top 20 Player Predictions',
      },
    },
    scales: {
      x: {
        ticks: {
          autoSkip: false,
          maxRotation: 90,
          minRotation: 90
        }
      }
    }
  };

  const scatterData = {
    datasets: [
      {
        label: 'Predicted Points vs Confidence',
        data: predictions.slice(0, 50).map(p => ({
          x: p.predicted_points,
          y: p.confidence_interval,
          player: p.player_name
        })),
        backgroundColor: 'rgba(153, 102, 255, 0.6)',
      },
    ],
  };

  const scatterOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Predicted Points vs Confidence Interval',
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const point = context.raw;
            return `${point.player}: (${point.x.toFixed(2)}, ${point.y.toFixed(2)})`;
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Predicted Points'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Confidence Interval'
        }
      }
    }
  };

  return (
    <div>
      <h1>Latest Predictions</h1>
      
      <div className="dashboard-card">
        <h2>Prediction Data</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Player Name</th>
                <th>Gameweek</th>
                <th>Predicted Points</th>
                <th>Confidence</th>
                <th>Model Version</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((pred) => (
                <tr key={pred.id}>
                  <td>{pred.id}</td>
                  <td>{pred.player_name}</td>
                  <td>{pred.gameweek}</td>
                  <td>{pred.predicted_points?.toFixed(2)}</td>
                  <td>{pred.confidence_interval?.toFixed(2)}</td>
                  <td>{pred.model_version}</td>
                  <td>{pred.created_at ? new Date(pred.created_at).toLocaleDateString() : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="dashboard-card">
        <h2>Prediction Analysis</h2>
        <div className="chart-container">
          <Bar data={histogramData} options={histogramOptions} />
        </div>
      </div>

      <div className="dashboard-card">
        <h2>Confidence Analysis</h2>
        <div className="chart-container">
          <Scatter data={scatterData} options={scatterOptions} />
        </div>
      </div>
    </div>
  );
};

export default Predictions;