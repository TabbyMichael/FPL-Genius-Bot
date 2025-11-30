import asyncio
import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from config.settings import FPL_USERNAME, FPL_PASSWORD, TEAM_ID
from config.database import get_db, PlayerPerformance
from services.fpl_api import FPLAPI
from services.transfer_engine import TransferEngine
from services.lineup_selector import LineupSelector
from services.ml_predictor import MLPredictor
from services.performance_analyzer import PerformanceAnalyzer
from utils.helpers import format_currency, calculate_squad_value

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fpl_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def record_performance_data(db: Session, player_data: Dict[str, Any], gameweek: int):
    """Record player performance data for ML training"""
    try:
        performance_record = PlayerPerformance(
            player_id=player_data.get('id'),
            gameweek=gameweek,
            expected_points=player_data.get('expected_points', 0),
            actual_points=player_data.get('event_points', 0),
            opponent_difficulty=player_data.get('opponent_difficulty', 3),
            minutes_played=player_data.get('minutes', 0),
            goals_scored=player_data.get('goals_scored', 0),
            assists=player_data.get('assists', 0),
            clean_sheet=player_data.get('clean_sheets', 0) > 0
        )
        db.add(performance_record)
        db.commit()
        logger.debug(f"Recorded performance data for player {player_data.get('web_name')}")
    except Exception as e:
        logger.error(f"Error recording performance data: {str(e)}")
        db.rollback()

async def get_current_squad(api: FPLAPI, gameweek: int):
    """Get the current squad for the team"""
    try:
        # Get team picks for current gameweek
        picks_data = await api.get_team_picks(gameweek)
        if not picks_data:
            logger.warning("Could not fetch team picks")
            return [], 1000  # Return empty squad with default budget
        
        picks = picks_data.get('picks', [])
        entry_history = picks_data.get('entry_history', {})
        
        # Get bootstrap data to map player IDs to player info
        bootstrap_data = await api.get_bootstrap_data()
        if not bootstrap_data:
            logger.warning("Could not fetch bootstrap data")
            return [], entry_history.get('bank', 1000)
        
        players = bootstrap_data.get('elements', [])
        player_dict = {player['id']: player for player in players}
        
        # Build squad with actual player data
        squad = []
        for pick in picks:
            player_id = pick.get('element')
            if player_id in player_dict:
                player_info = player_dict[player_id].copy()
                player_info['pick_data'] = pick  # Include pick-specific data
                squad.append(player_info)
        
        bank = entry_history.get('bank', 1000)  # Bank in tenths of million
        return squad, bank
    except Exception as e:
        logger.error(f"Error getting current squad: {str(e)}")
        return [], 1000  # Return empty squad with default budget

async def analyze_top_performers(api: FPLAPI, analyzer: PerformanceAnalyzer, players: List[Dict[str, Any]]):
    """Analyze top performing players and teams"""
    try:
        logger.info("Analyzing top performers...")
        
        # Get top players by position
        gk_players = await analyzer.get_top_players_by_position(players, 1, 3)
        def_players = await analyzer.get_top_players_by_position(players, 2, 5)
        mid_players = await analyzer.get_top_players_by_position(players, 3, 5)
        fwd_players = await analyzer.get_top_players_by_position(players, 4, 3)
        
        logger.info("Top Goalkeepers:")
        for i, player in enumerate(gk_players, 1):
            logger.info(f"  {i}. {player.get('web_name')} - £{player.get('now_cost', 0)/10:.1f}m (Form: {player.get('form', 0)})")
        
        logger.info("Top Defenders:")
        for i, player in enumerate(def_players, 1):
            logger.info(f"  {i}. {player.get('web_name')} - £{player.get('now_cost', 0)/10:.1f}m (Form: {player.get('form', 0)})")
        
        logger.info("Top Midfielders:")
        for i, player in enumerate(mid_players, 1):
            logger.info(f"  {i}. {player.get('web_name')} - £{player.get('now_cost', 0)/10:.1f}m (Form: {player.get('form', 0)})")
        
        logger.info("Top Forwards:")
        for i, player in enumerate(fwd_players, 1):
            logger.info(f"  {i}. {player.get('web_name')} - £{player.get('now_cost', 0)/10:.1f}m (Form: {player.get('form', 0)})")
        
        # Get differential players
        differential_players = await analyzer.get_differential_players(players, 5.0)
        logger.info("Differential Picks (Selected < 5%):")
        for i, player in enumerate(differential_players[:5], 1):
            logger.info(f"  {i}. {player.get('web_name')} - £{player.get('now_cost', 0)/10:.1f}m (Selected: {player.get('selected_by_percent', 0)}%)")
        
    except Exception as e:
        logger.error(f"Error analyzing top performers: {str(e)}")

async def execute_transfers(api: FPLAPI, transfers: List[Dict[str, Any]], current_squad: List[Dict[str, Any]]):
    """Execute transfers (placeholder for actual implementation)"""
    try:
        if not transfers:
            logger.info("No transfers to execute")
            return True
        
        logger.info("Executing transfers...")
        for transfer in transfers:
            out_player = transfer['out']
            in_player = transfer['in']
            logger.info(f"Transferring out: {out_player.get('web_name')} -> Transferring in: {in_player.get('web_name')}")
            logger.info(f"  Reason: {transfer.get('reason', 'No reason provided')}")
            
            # In a real implementation, this would make actual API calls to execute transfers
            # This requires proper authentication and is beyond the scope of this example
            # For now, we'll just log what would be transferred
        
        logger.info("Transfer execution completed (simulated)")
        return True
    except Exception as e:
        logger.error(f"Error executing transfers: {str(e)}")
        return False

async def run_weekly_process():
    """Run the weekly FPL process"""
    logger.info("Starting weekly FPL process")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    async with FPLAPI() as api:
        # 1. Fetch bootstrap data
        logger.info("Fetching FPL data...")
        bootstrap_data = await api.get_bootstrap_data()
        if not bootstrap_data:
            logger.error("Failed to fetch bootstrap data")
            return False
        
        # 2. Get player data
        players = bootstrap_data.get('elements', [])
        teams = bootstrap_data.get('teams', [])
        events = bootstrap_data.get('events', [])
        
        # 3. Find current gameweek
        current_gw = None
        for event in events:
            if event.get('is_current'):
                current_gw = event
                break
        
        # If no current gameweek, try next
        if not current_gw:
            for event in events:
                if event.get('is_next'):
                    current_gw = event
                    break
        
        if not current_gw:
            logger.warning("Could not determine current gameweek")
            return False
            
        gameweek_id = current_gw.get('id')
        logger.info(f"Processing gameweek {gameweek_id}")
        
        # 4. Get current squad
        logger.info("Fetching current squad...")
        current_squad, budget = await get_current_squad(api, gameweek_id)
        
        # If we couldn't get the squad for the determined gameweek, try the previous one
        if len(current_squad) == 0 and gameweek_id > 1:
            logger.info(f"Trying previous gameweek {gameweek_id - 1}")
            current_squad, budget = await get_current_squad(api, gameweek_id - 1)
            if len(current_squad) > 0:
                gameweek_id = gameweek_id - 1
                logger.info(f"Successfully loaded squad from gameweek {gameweek_id}")
        
        logger.info(f"Loaded squad with {len(current_squad)} players")
        logger.info(f"Available budget: {format_currency(budget)}")
        
        # Display some squad info
        if current_squad:
            logger.info("Current squad:")
            for player in current_squad:
                pick_data = player.get('pick_data', {})
                multiplier = pick_data.get('multiplier', 1)
                position = pick_data.get('position', 0)
                role = ""
                if multiplier == 2:
                    role = " (Captain)"
                elif multiplier == 3:
                    role = " (Vice-Captain)"
                elif multiplier == 0:
                    role = " (Bench)"
                
                # Get team name
                team_id = player.get('team', 0)
                team_name = "Unknown"
                for team in teams:
                    if team.get('id') == team_id:
                        team_name = team.get('name', 'Unknown')
                        break
                
                logger.info(f"  {position}. {player.get('web_name', 'Unknown')} - {team_name} - £{player.get('now_cost', 0)/10:.1f}m{role}")
        else:
            logger.warning("No squad data available")
        
        # 5. Initialize engines with database connection
        transfer_engine = TransferEngine(db)
        lineup_selector = LineupSelector(db)
        performance_analyzer = PerformanceAnalyzer(api)
        
        # Record performance data for ML training (would normally be from previous gameweeks)
        for player in players[:20]:  # More sample data for demonstration
            await record_performance_data(db, player, gameweek_id - 1)
        
        # Retrain ML model with new data
        ml_predictor = MLPredictor()
        await asyncio.get_event_loop().run_in_executor(None, lambda: ml_predictor.train_model(db))
        
        # Show feature importance if model is trained
        if ml_predictor.is_trained:
            feature_importance = ml_predictor.get_feature_importance()
            logger.info("ML Model Feature Importance:")
            for feature, importance in list(feature_importance.items())[:5]:  # Top 5 features
                logger.info(f"  {feature}: {importance:.3f}")
        
        # 6. Analyze top performers
        await analyze_top_performers(api, performance_analyzer, players)
        
        # 7. Identify transfer targets with sophisticated analysis
        logger.info("Analyzing transfer options with fixture difficulty and injury checks...")
        transfer_targets = await transfer_engine.identify_transfer_targets(
            current_squad, players, budget, api
        )
        
        logger.info(f"Found {len(transfer_targets)} potential transfers")
        for transfer in transfer_targets:
            out_player = transfer['out']
            in_player = transfer['in']
            reason = transfer.get('reason', 'No reason provided')
            logger.info(f"Consider: {out_player.get('web_name')} -> {in_player.get('web_name')}")
            logger.info(f"  Gain: {transfer['gain']:.2f} value points")
            logger.info(f"  Expected point gain: {transfer['expected_point_gain']:.2f} points")
            logger.info(f"  Reason: {reason}")
            
            # Record transfer consideration for analysis
            transfer_engine.record_transfer({
                'out': out_player,
                'in': in_player,
                'gain': transfer['gain'],
                'gameweek': gameweek_id,
                'cost': 0  # Would be actual transfer cost
            })
        
        # 8. Execute transfers (simulated)
        await execute_transfers(api, transfer_targets, current_squad)
        
        # 9. Select lineup
        logger.info("Selecting optimal lineup...")
        lineup = lineup_selector.select_lineup(current_squad)
        captain = lineup_selector.select_captain(lineup)
        
        if captain:
            # Get captain's team name
            captain_team_id = captain.get('team', 0)
            captain_team_name = "Unknown"
            for team in teams:
                if team.get('id') == captain_team_id:
                    captain_team_name = team.get('name', 'Unknown')
                    break
            logger.info(f"Selected captain: {captain.get('web_name')} ({captain_team_name})")
        else:
            logger.warning("No captain selected")
        
        # 10. Log squad summary
        if current_squad:
            squad_value = calculate_squad_value(current_squad)
            logger.info(f"Squad value: {format_currency(squad_value)}")
        
        # Show upcoming fixture difficulties
        logger.info("Upcoming fixture difficulties:")
        current_teams = set(player.get('team') for player in current_squad)
        for team in teams:
            if team.get('id') in current_teams:
                difficulty = await api.get_fixture_difficulty(team.get('id'), gameweek_id)
                logger.info(f"  {team.get('name')}: Difficulty {difficulty}/5")
        
        # Check for injured players in squad
        injured_players = [player for player in current_squad if not transfer_engine.is_player_available(player)]
        if injured_players:
            logger.warning(f"Found {len(injured_players)} potentially unavailable players in squad:")
            for player in injured_players:
                injury_info = await api.get_player_injury_status(player.get('id'))
                # Handle different return types from get_player_injury_status
                news = "No news available"
                if isinstance(injury_info, dict):
                    news = injury_info.get('news', 'No news available')
                elif isinstance(injury_info, str):
                    news = injury_info
                logger.warning(f"  {player.get('web_name')}: {news}")
        
        logger.info("Weekly process completed successfully")
        return True

async def main():
    """Main entry point for the FPL bot"""
    logger.info("=" * 50)
    logger.info("FPL Bot Starting")
    logger.info("=" * 50)
    
    try:
        success = await run_weekly_process()
        if success:
            logger.info("FPL Bot completed successfully")
        else:
            logger.error("FPL Bot encountered errors")
            return 1
            
    except Exception as e:
        logger.error(f"Error running FPL Bot: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)