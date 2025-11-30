import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# Configure the page
st.set_page_config(
    page_title="FPL Bot Dashboard",
    page_icon="⚽",
    layout="wide"
)

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def fetch_data(endpoint):
    """Fetch data from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data from {endpoint}: {str(e)}")
        return None

def main():
    st.title("⚽ FPL Bot Dashboard")
    st.markdown("Monitor and control your Fantasy Premier League bot")

    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio("Go to", [
        "Overview", 
        "Performance History", 
        "Predictions", 
        "Transfer History",
        "Health Status"
    ])

    if page == "Overview":
        show_overview()
    elif page == "Performance History":
        show_performance_history()
    elif page == "Predictions":
        show_predictions()
    elif page == "Transfer History":
        show_transfer_history()
    elif page == "Health Status":
        show_health_status()

def show_overview():
    st.header("Overview")
    
    # Fetch analytics summary
    summary = fetch_data("/analytics/summary")
    if summary:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Predictions", summary.get("total_predictions", 0))
        
        with col2:
            st.metric("Total Performances", summary.get("total_performances", 0))
        
        with col3:
            st.metric("Total Transfers", summary.get("total_transfers", 0))
        
        with col4:
            st.metric("Latest Gameweek", summary.get("latest_gameweek", 0))
    
    # Show team info
    team_info = fetch_data("/team/info")
    if team_info:
        st.subheader("Team Information")
        st.write(f"Team ID: {team_info.get('team_id', 'Not configured')}")

def show_performance_history():
    st.header("Performance History")
    
    # Fetch performance data
    performances = fetch_data("/performance/history?limit=100")
    if performances and isinstance(performances, list):
        df = pd.DataFrame(performances)
        
        if not df.empty:
            # Display as table
            st.dataframe(df)
            
            # Create charts
            st.subheader("Performance Trends")
            
            # Points comparison chart
            if 'expected_points' in df.columns and 'actual_points' in df.columns:
                fig = px.scatter(df, x='expected_points', y='actual_points', 
                               title="Expected vs Actual Points",
                               hover_data=['gameweek', 'player_id'])
                st.plotly_chart(fig, use_container_width=True)
            
            # Form trend
            if 'form' in df.columns:
                fig2 = px.line(df, x='created_at', y='form', 
                              title="Player Form Over Time")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No performance data available")
    else:
        st.warning("Unable to fetch performance data")

def show_predictions():
    st.header("Latest Predictions")
    
    # Fetch predictions
    predictions = fetch_data("/predictions/latest?limit=100")
    if predictions and isinstance(predictions, list):
        df = pd.DataFrame(predictions)
        
        if not df.empty:
            # Display as table
            st.dataframe(df)
            
            # Create charts
            st.subheader("Prediction Analysis")
            
            # Points distribution
            if 'predicted_points' in df.columns:
                fig = px.histogram(df, x='predicted_points', 
                                 title="Distribution of Predicted Points")
                st.plotly_chart(fig, use_container_width=True)
            
            # Confidence interval
            if 'confidence_interval' in df.columns:
                fig2 = px.scatter(df, x='predicted_points', y='confidence_interval',
                                title="Predicted Points vs Confidence Interval")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No prediction data available")
    else:
        st.warning("Unable to fetch prediction data")

def show_transfer_history():
    st.header("Transfer History")
    
    # Fetch transfer history
    transfers = fetch_data("/transfers/history?limit=100")
    if transfers and isinstance(transfers, list):
        df = pd.DataFrame(transfers)
        
        if not df.empty:
            # Display as table
            st.dataframe(df)
            
            # Create charts
            st.subheader("Transfer Analysis")
            
            # Transfers over time
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                fig = px.scatter(df, x='timestamp', y='transfer_gain',
                               title="Transfer Gains Over Time")
                st.plotly_chart(fig, use_container_width=True)
            
            # Cost analysis
            if 'cost' in df.columns:
                fig2 = px.histogram(df, x='cost', title="Transfer Costs Distribution")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No transfer history available")
    else:
        st.warning("Unable to fetch transfer history")

def show_health_status():
    st.header("Health Status")
    
    # Fetch health status
    health = fetch_data("/health")
    if health:
        status = health.get("status", "unknown")
        details = health.get("details", {})
        
        # Display overall status
        if status == "healthy":
            st.success(f"✅ System Status: {status.upper()}")
        else:
            st.error(f"❌ System Status: {status.upper()}")
        
        # Display details
        st.subheader("Component Status")
        for component, is_healthy in details.items():
            if is_healthy:
                st.markdown(f"✅ {component}: Healthy")
            else:
                st.markdown(f"❌ {component}: Unhealthy")
    else:
        st.warning("Unable to fetch health status")

if __name__ == "__main__":
    main()