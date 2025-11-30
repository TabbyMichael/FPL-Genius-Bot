import React from 'react';
import './Team.css';

const Player = ({ player }) => {
  return (
    <div className="player">
      <div className="player-shirt"></div>
      <div className="player-info">
        <span className="player-name">{player.player_name}</span>
        <span className="player-points">{player.actual_points}</span>
      </div>
    </div>
  );
};

export default Player;
