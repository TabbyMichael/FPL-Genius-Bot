from fastapi import FastAPI, Depends, HTTPException
from typing import Optional
import os

from .api import FPLAPI

app = FastAPI(
    title="FPL API Service",
    description="A microservice to interact with the official FPL API.",
    version="1.0.0"
)

# A single, shared FPLAPI client instance
# In a real-world scenario, you might manage this differently,
# but for this service, a single instance is fine.
fpl_api_client = FPLAPI(
    username=os.getenv("FPL_USERNAME"),
    password=os.getenv("FPL_PASSWORD"),
    session_id=os.getenv("SESSION_ID"),
    csrf_token=os.getenv("CSRF_TOKEN"),
    team_id=os.getenv("TEAM_ID"),
)

@app.on_event("startup")
async def startup_event():
    # This will create the underlying session
    await fpl_api_client.__aenter__()

@app.on_event("shutdown")
async def shutdown_event():
    await fpl_api_client.__aexit__(None, None, None)

@app.get("/bootstrap")
async def get_bootstrap_data():
    """
    Get the main FPL bootstrap data (players, teams, etc.).
    """
    data = await fpl_api_client.get_bootstrap_data()
    if data is None:
        raise HTTPException(status_code=503, detail="Failed to fetch bootstrap data from FPL API.")
    return data

@app.get("/fixtures")
async def get_fixtures_data():
    """
    Get the fixture list for the season.
    """
    data = await fpl_api_client.get_fixtures()
    if data is None:
        raise HTTPException(status_code=503, detail="Failed to fetch fixtures data from FPL API.")
    return data

@app.get("/player/{player_id}")
async def get_player_summary(player_id: int):
    """
    Get a summary for a specific player.
    """
    data = await fpl_api_client.get_player_data(player_id)
    if data is None:
        raise HTTPException(status_code=503, detail=f"Failed to fetch player data for player {player_id}.")
    return data

@app.get("/team/{team_id}/picks/{gameweek}")
async def get_team_picks(team_id: int, gameweek: int):
    """
    Get a manager's team picks for a specific gameweek.
    Note: This requires authentication.
    """
    # This assumes the service is configured with the correct team_id for auth
    if str(team_id) != fpl_api_client.team_id:
        raise HTTPException(status_code=403, detail="Can only fetch picks for the configured team.")

    data = await fpl_api_client.get_team_picks(gameweek)
    if data is None:
        raise HTTPException(status_code=503, detail="Failed to fetch team picks.")
    return data
