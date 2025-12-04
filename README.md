# FPL Genius Bot

An advanced Fantasy Premier League (FPL) bot that automatically analyzes top performers, makes intelligent transfer recommendations, and executes transfers. Features include machine learning predictions, fixture difficulty analysis, injury/suspension checking, and performance tracking. Supports Google Sign-In authentication and scheduled weekly execution via GitHub Actions.

## Features

- **Performance Analysis**: Identifies top performing teams and players in FPL
- **Smart Transfers**: Makes intelligent transfer recommendations based on value, form, and fixture difficulty
- **ML Predictions**: Uses machine learning to predict player performance
- **Injury/Suspension Checking**: Considers player availability in recommendations
- **Transfer Execution**: Framework for executing transfers (supports Google Sign-In)
- **Performance Tracking**: Stores data in database for continuous improvement
- **Scheduled Execution**: Runs automatically via GitHub Actions
- **Health Monitoring**: Built-in health checks for API, database, and ML model status
- **Comprehensive Testing**: Full test suite with pytest

![TradeZella Banner](/dashboard/react/public/assets/1.png)

## Project Structure

```
fpl-genius-bot/
├── bot.py                 # Main bot logic
├── transfer_demo.py       # Transfer execution demo
├── run_tests.py           # Test runner script
├── config/
│   ├── settings.py        # Configuration settings
│   └── database.py        # Database models and connections
├── services/
│   ├── fpl_api.py         # FPL API communication
│   ├── transfer_engine.py # Transfer decision logic
│   ├── lineup_selector.py # Lineup optimization
│   ├── ml_predictor.py    # Machine learning predictions
│   ├── performance_analyzer.py # Performance analysis
│   ├── health_check.py    # System health monitoring
├── tests/
│   ├── test_fpl_api.py    # Tests for FPL API service
│   ├── test_transfer_engine.py # Tests for transfer engine
│   ├── test_ml_predictor.py # Tests for ML predictor
│   ├── test_integration.py # Integration tests
│   └── conftest.py        # Pytest configuration
├── utils/
│   └── helpers.py         # Utility functions
├── .github/workflows/
│   └── fpl_bot.yml        # GitHub Actions workflow
├── requirements.txt       # Python dependencies
├── requirements-dev.txt   # Development dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Setup

### 1. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 3. Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```

Edit the `.env` file to add your FPL credentials:
```bash
# For traditional FPL accounts:
FPL_USERNAME=your_email@example.com
FPL_PASSWORD=your_password

# For Google Sign-In accounts:
# Extract session cookies from your browser after logging in
SESSION_ID=your_sessionid_cookie_value
CSRF_TOKEN=your_csrftoken_cookie_value

TEAM_ID=your_team_id

# Database Configuration
DATABASE_URL=sqlite:///./fpl_bot.db
```

### 4. Initialize Database
```bash
# The database is automatically initialized when the bot runs
```
dashboard/react/public/assets/2.png

## Security Best Practices

### Environment Variables and Secrets
- **Never commit sensitive data** to version control
- All sensitive information should be stored in `.env` files
- The `.gitignore` file ensures `.env` files are not committed
- Use `.env.example` as a template for other developers (this file can be committed)

### For Google Sign-In Accounts
If you use Google Sign-In for FPL:
1. Log into FPL manually in your browser
2. Open Developer Tools (F12)
3. Go to Application > Cookies > https://fantasy.premierleague.com
4. Copy the values for:
   - `sessionid` → Set as `SESSION_ID` in `.env`
   - `csrftoken` → Set as `CSRF_TOKEN` in `.env`

### Example .env File
```bash
# FPL Credentials (choose one method)
# Method 1: Traditional login
FPL_USERNAME=your_email@example.com
FPL_PASSWORD=your_secure_password

# Method 2: Google Sign-In (session-based)
SESSION_ID=extracted_from_browser_cookies
CSRF_TOKEN=extracted_from_browser_cookies

TEAM_ID=1234567

# Database Configuration
DATABASE_URL=sqlite:///./fpl_bot.db

# Bot Settings
LOG_LEVEL=INFO
LOG_FILE=logs/fpl_bot.log

# ML Model Settings
ML_TRAINING_DATA_MIN=50
```
dashboard/react/public/assets/3.png

## Usage

### Run Performance Analysis and Transfer Recommendations
```bash
python bot.py
```

### Test Transfer Execution (Demo)
```bash
python transfer_demo.py
```

### Run All Tests
```bash
python run_tests.py
```

### Run Specific Tests
```bash
# Run tests with pytest directly
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=services --cov-report=html
```

### View Logs
```bash
tail -f logs/fpl_bot.log
```

## GitHub Actions

The bot is scheduled to run weekly using GitHub Actions:
- **Schedule**: Every Friday at 7 AM UTC
- **Trigger**: Automatically runs without manual intervention
- **Configuration**: Located in `.github/workflows/fpl_bot.yml`

To use GitHub Actions:
1. Push this repository to GitHub
2. Add your secrets in GitHub Repository Settings:
   - `FPL_USERNAME` (if using traditional login)
   - `FPL_PASSWORD` (if using traditional login)
   - `SESSION_ID` (if using Google Sign-In)
   - `CSRF_TOKEN` (if using Google Sign-In)
   - `TEAM_ID`
   - `DATABASE_URL` (optional, defaults to SQLite)

## Database

The bot uses SQLite by default for easy setup:
- **Default**: `sqlite:///./fpl_bot.db`
- **Alternative**: PostgreSQL can be configured in `.env`

Tables:
- `player_performance`: Tracks player performance data
- `player_predictions`: Stores ML predictions
- `transfer_history`: Records transfer decisions

dashboard/react/public/assets/4.png

## Machine Learning

The bot uses Random Forest Regression to predict player performance based on:
- Historical performance data
- Fixture difficulty
- Minutes played
- Goals scored
- Assists
- Clean sheets
- Yellow/red cards
- Saves
- Bonus points
- Form ratings
- Selection percentages
- Transfer movements

Features improve over time as the bot collects more data.

## Health Monitoring

The bot includes built-in health checks:
- **API Connectivity**: Verifies FPL API accessibility
- **Database Connectivity**: Checks database connection
- **ML Model Status**: Verifies model training status
- **Error Tracking**: Logs and reports system errors

Run health checks manually:
```bash
python -c "from services.health_check import get_health_report; import asyncio; print(asyncio.run(get_health_report()))"
```

## Risk Mitigation

### FPL API Changes
- **Adapter Pattern**: API interactions are encapsulated in the FPLAPI service
- **Version Compatibility**: Regular health checks detect API issues
- **Fallback Data Sources**: Graceful degradation when API fails

### Rate Limiting
- **Request Throttling**: Built-in delays between API requests
- **Caching Strategies**: Data caching reduces API calls
- **Retry Mechanisms**: Exponential backoff for failed requests

### Data Quality Issues
- **Data Validation**: Input validation for all data sources
- **Anomaly Detection**: Statistical analysis identifies outliers
- **Quality Monitoring**: Continuous monitoring of data integrity

## Technical Debt Management

### Short-term Improvements (1-2 weeks)
- ✅ Fix ML model training to show meaningful feature importance
- ✅ Implement proper error handling with timeouts
- ✅ Add comprehensive logging for debugging
- ✅ Complete transfer execution implementation

### Medium-term Improvements (1-2 months)
- ✅ Implement automated authentication refresh
- ✅ Add unit tests for all services
- ✅ Improve data quality and collection processes
- ✅ Create health check mechanisms

### Long-term Improvements (3-6 months)
- ✅ Refactor to microservices architecture (planned)
- ✅ Implement advanced analytics and reporting (planned)
- ✅ Add A/B testing for different strategies (planned)
- ✅ Create web dashboard for monitoring and control (planned)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Running Tests

The project includes a comprehensive test suite:

```bash
# Run all tests
python run_tests.py

# Run specific test files
pytest tests/test_fpl_api.py -v

# Run tests with coverage
pytest tests/ --cov=services --cov-report=term-missing

# Run linting
flake8 services/ config/ utils/ tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This bot is for educational purposes only. Use at your own risk. 
Always遵守 FPL Terms of Service.
