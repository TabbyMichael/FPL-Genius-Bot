import React from 'react';
import './PerformanceHistoryTable.css';

const PerformanceHistoryTable = ({ performances }) => {
  if (!performances || performances.length === 0) {
    return (
      <div className="dashboard-card">
        <p>No performance history available for the selected filters.</p>
      </div>
    );
  }

  return (
    <div className="dashboard-card">
      <div className="table-container">
        <table className="performance-table">
          <thead>
            <tr>
              <th>Player Name</th>
              <th>Gameweek</th>
              <th>Expected Points</th>
              <th>Actual Points</th>
              <th>Form</th>
              <th>Pts/Game</th>
              <th>Opponent Difficulty</th>
            </tr>
          </thead>
          <tbody>
            {performances.map((p) => (
              <tr key={p.id}>
                <td>{p.player_name}</td>
                <td>{p.gameweek}</td>
                <td>{p.expected_points.toFixed(2)}</td>
                <td>{p.actual_points.toFixed(0)}</td>
                <td>{p.form.toFixed(2)}</td>
                <td>{p.points_per_game.toFixed(2)}</td>
                <td>{p.opponent_difficulty}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PerformanceHistoryTable;