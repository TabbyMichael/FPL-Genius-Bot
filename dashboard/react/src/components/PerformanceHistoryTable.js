import React from 'react';
import './PerformanceHistoryTable.css';

const PerformanceHistoryTable = ({ performances }) => {
  if (!performances || performances.length === 0) {
    return <p>No performance history available.</p>;
  }

  return (
    <div className="table-container">
      <table className="performance-table">
        <thead>
          <tr>
            <th>Player Name</th>
            <th>Gameweek</th>
            <th>Expected Points</th>
            <th>Actual Points</th>
          </tr>
        </thead>
        <tbody>
          {performances.map((p) => (
            <tr key={p.id}>
              <td>{p.player_name}</td>
              <td>{p.gameweek}</td>
              <td>{p.expected_points.toFixed(2)}</td>
              <td>{p.actual_points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PerformanceHistoryTable;
