import React from 'react';
import Player from './Player';
import './Team.css';

const Field = ({ players }) => {
  const positions = {
    goalkeepers: players.filter(p => p.position === 'GKP'),
    defenders: players.filter(p => p.position === 'DEF'),
    midfielders: players.filter(p => p.position === 'MID'),
    forwards: players.filter(p => p.position === 'FWD'),
  };

  return (
    <div className="pitch">
      <div className="pitch-lines">
        <div className="pitch-line-top"></div>
        <div className="pitch-line-bottom"></div>
        <div className="pitch-line-left"></div>
        <div className="pitch-line-right"></div>
        <div className="pitch-line-middle"></div>
        <div className="pitch-circle-middle"></div>
        <div className="pitch-penalty-box-left"></div>
        <div className="pitch-penalty-box-right"></div>
      </div>
      <div className="team-formation">
        <div className="team-row">
          {positions.goalkeepers.map(player => <Player key={player.id} player={player} />)}
        </div>
        <div className="team-row">
          {positions.defenders.map(player => <Player key={player.id} player={player} />)}
        </div>
        <div className="team-row">
          {positions.midfielders.map(player => <Player key={player.id} player={player} />)}
        </div>
        <div className="team-row">
          {positions.forwards.map(player => <Player key={player.id} player={player} />)}
        </div>
      </div>
    </div>
  );
};

export default Field;
