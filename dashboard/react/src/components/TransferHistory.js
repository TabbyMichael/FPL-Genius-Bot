import React, { useState, useEffect } from 'react';
import { fetchTransferHistory } from '../services/api';
import { Scatter, Bar } from 'react-chartjs-2';
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

const TransferHistory = () => {
  const [transfers, setTransfers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetchTransferHistory(100);
        setTransfers(response.data);
      } catch (err) {
        setError('Failed to fetch transfer history');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading transfer history...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  // Prepare data for charts
  const scatterData = {
    datasets: [
      {
        label: 'Transfer Gains Over Time',
        data: transfers.slice(0, 50).map(t => ({
          x: t.timestamp ? new Date(t.timestamp).getTime() : 0,
          y: t.transfer_gain,
        })),
        backgroundColor: 'rgba(255, 99, 132, 0.6)',
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
        text: 'Transfer Gains Over Time',
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Date'
        },
        type: 'linear',
        ticks: {
          callback: function(value) {
            return new Date(value).toLocaleDateString();
          }
        }
      },
      y: {
        title: {
          display: true,
          text: 'Transfer Gain'
        }
      }
    }
  };

  const costData = {
    labels: transfers.slice(0, 20).map(t => `${t.player_out_name} → ${t.player_in_name}`),
    datasets: [
      {
        label: 'Transfer Costs',
        data: transfers.slice(0, 20).map(t => t.cost),
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
    ],
  };

  const costOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Recent Transfer Costs',
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

  return (
    <div>
      <h1>Transfer History</h1>
      
      <div className="dashboard-card">
        <h2>Transfer Data</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Player Out</th>
                <th>Player In</th>
                <th>Gameweek</th>
                <th>Gain</th>
                <th>Cost</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {transfers.map((transfer) => (
                <tr key={transfer.id}>
                  <td>{transfer.id}</td>
                  <td>{transfer.player_out_name}</td>
                  <td>{transfer.player_in_name}</td>
                  <td>{transfer.gameweek}</td>
                  <td>{transfer.transfer_gain?.toFixed(2)}</td>
                  <td>{transfer.cost}</td>
                  <td>{transfer.timestamp ? new Date(transfer.timestamp).toLocaleDateString() : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="dashboard-card">
        <h2>Transfer Analysis</h2>
        <div className="chart-container">
          <Scatter data={scatterData} options={scatterOptions} />
        </div>
      </div>

      <div className="dashboard-card">
        <h2>Cost Analysis</h2>
        <div className="chart-container">
          <Bar data={costData} options={costOptions} />
        </div>
      </div>
    </div>
  );
};

export default TransferHistory;