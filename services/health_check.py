import logging
import asyncio
from typing import Dict, Any
from services.fpl_api import FPLAPI
from config.database import get_db, PlayerPerformance
from config.settings import TEAM_ID

logger = logging.getLogger(__name__)

class HealthCheckService:
    """Service to monitor and report on bot health"""
    
    def __init__(self):
        self.status = {
            'api_connectivity': False,
            'database_connectivity': False,
            'ml_model_trained': False,
            'last_run_time': None,
            'errors': []
        }
    
    async def check_api_connectivity(self) -> bool:
        """Check if FPL API is accessible"""
        try:
            async with FPLAPI() as api:
                data = await api.get_bootstrap_data()
                if data and 'elements' in data:
                    logger.info("FPL API connectivity check passed")
                    return True
                else:
                    logger.warning("FPL API returned unexpected data")
                    return False
        except Exception as e:
            logger.error(f"FPL API connectivity check failed: {str(e)}")
            self.status['errors'].append(f"API: {str(e)}")
            return False
    
    def check_database_connectivity(self) -> bool:
        """Check if database is accessible"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            # Try a simple query
            count = db.query(PlayerPerformance).count()
            db.close()
            logger.info(f"Database connectivity check passed ({count} records)")
            return True
        except Exception as e:
            logger.error(f"Database connectivity check failed: {str(e)}")
            self.status['errors'].append(f"DB: {str(e)}")
            return False
    
    def check_ml_model_status(self, ml_predictor=None) -> bool:
        """Check if ML model is trained by checking database records"""
        try:
            # Check if we have performance data which indicates the model has been trained
            db_gen = get_db()
            db = next(db_gen)
            count = db.query(PlayerPerformance).count()
            db.close()
            
            # If we have performance data, consider the model as trained
            is_trained = count > 0
            if is_trained:
                logger.info("ML model status check passed (data available)")
            else:
                logger.warning("ML model is not trained (no performance data)")
            return is_trained
        except Exception as e:
            logger.error(f"ML model status check failed: {str(e)}")
            self.status['errors'].append(f"ML: {str(e)}")
            return False
    
    async def run_health_checks(self, ml_predictor=None) -> Dict[str, Any]:
        """Run all health checks and return status"""
        logger.info("Running health checks...")
        
        # Reset errors
        self.status['errors'] = []
        
        # Run checks
        self.status['api_connectivity'] = await self.check_api_connectivity()
        self.status['database_connectivity'] = self.check_database_connectivity()
        self.status['ml_model_trained'] = self.check_ml_model_status(ml_predictor)
        
        # Update last run time
        from datetime import datetime
        self.status['last_run_time'] = datetime.now().isoformat()
        
        # Determine overall health
        critical_checks = [
            self.status['api_connectivity'],
            self.status['database_connectivity']
        ]
        
        if all(critical_checks):
            logger.info("All critical health checks passed")
        else:
            logger.warning(f"Some health checks failed: {critical_checks}")
        
        return self.status
    
    def get_health_report(self) -> str:
        """Generate a human-readable health report"""
        report = "=== FPL Bot Health Report ===\n"
        report += f"Last Check: {self.status.get('last_run_time', 'Never')}\n"
        report += f"API Connectivity: {'✓' if self.status.get('api_connectivity') else '✗'}\n"
        report += f"Database Connectivity: {'✓' if self.status.get('database_connectivity') else '✗'}\n"
        report += f"ML Model Trained: {'✓' if self.status.get('ml_model_trained') else '✗'}\n"
        
        if self.status['errors']:
            report += "\nErrors:\n"
            for error in self.status['errors'][:5]:  # Limit to first 5 errors
                report += f"  - {error}\n"
        
        return report

# Convenience function to run health checks
async def run_health_check(ml_predictor=None) -> Dict[str, Any]:
    """Convenience function to run health checks"""
    health_service = HealthCheckService()
    return await health_service.run_health_checks(ml_predictor)

# Convenience function to get health report
async def get_health_report(ml_predictor=None) -> str:
    """Convenience function to get health report"""
    health_service = HealthCheckService()
    await health_service.run_health_checks(ml_predictor)
    return health_service.get_health_report()