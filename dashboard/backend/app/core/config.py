import os
import logging
from dotenv import load_dotenv
from pydantic import BaseSettings
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Settings for the dashboard backend."""
    
    # Connection URLs for external services
    GNS3_URL: str = os.getenv("GNS3_URL", "http://localhost:3080")
    # For local development, use localhost. For Docker, set COLLECTOR_URL=http://host.docker.internal:8083
    COLLECTOR_URL: str = os.getenv("COLLECTOR_URL", "http://localhost:8083")
    POLICY_ENGINE_URL: str = os.getenv("POLICY_ENGINE_URL", "http://localhost:5000")
    
    # Connection settings
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "10"))  # 10 seconds
    CONNECTION_RETRIES: int = int(os.getenv("CONNECTION_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "2"))  # seconds
    
    # Health check settings
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds
    STARTUP_TIMEOUT: int = int(os.getenv("STARTUP_TIMEOUT", "30"))  # seconds - reduced since GNS3 is optional
    
    # Version information
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    BUILD_DATE: str = os.getenv("BUILD_DATE", "unknown")
    GIT_COMMIT: str = os.getenv("GIT_COMMIT", "unknown")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Legacy version fields for compatibility
    VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    LAST_UPDATED: str = os.getenv("BUILD_DATE", "unknown")
    DESCRIPTION: str = f"MicroFed Dashboard API v{os.getenv('APP_VERSION', '1.0.0')}"
    
    # Other settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SCENARIOS_DIR: str = os.getenv("SCENARIOS_DIR", "/app/src/scenarios")
    
    # Database settings
    database_url: str = "sqlite:///./app.db"
    
    # API settings
    api_title: str = "Dashboard Backend API"
    api_version: str = "1.0.0"
    api_description: str = "Backend API for the FLOPY-NET Dashboard"
    
    # CORS settings
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8085",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:8085",
        "http://host.docker.internal:8085"
    ]
    
    # Dashboard Performance and Limits Configuration
    # These replace hardcoded values throughout the dashboard
    
    # API Request Limits
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "100"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "500"))
    MAX_FL_ROUNDS_LIMIT: int = int(os.getenv("MAX_FL_ROUNDS_LIMIT", "5000"))
    DEFAULT_EVENTS_LIMIT: int = int(os.getenv("DEFAULT_EVENTS_LIMIT", "1000"))
    
    # Performance Thresholds
    FL_ACCURACY_GOOD_THRESHOLD: float = float(os.getenv("FL_ACCURACY_GOOD_THRESHOLD", "80.0"))  # 80%
    FL_ACCURACY_WARNING_THRESHOLD: float = float(os.getenv("FL_ACCURACY_WARNING_THRESHOLD", "50.0"))  # 50%
    FL_LOSS_GOOD_THRESHOLD: float = float(os.getenv("FL_LOSS_GOOD_THRESHOLD", "0.1"))  # 0.1
    FL_LOSS_WARNING_THRESHOLD: float = float(os.getenv("FL_LOSS_WARNING_THRESHOLD", "0.5"))  # 0.5
    
    # Network Performance Thresholds  
    NETWORK_LATENCY_GOOD_THRESHOLD: float = float(os.getenv("NETWORK_LATENCY_GOOD_THRESHOLD", "10.0"))  # 10ms
    NETWORK_LATENCY_WARNING_THRESHOLD: float = float(os.getenv("NETWORK_LATENCY_WARNING_THRESHOLD", "50.0"))  # 50ms
    NETWORK_PACKET_LOSS_GOOD_THRESHOLD: float = float(os.getenv("NETWORK_PACKET_LOSS_GOOD_THRESHOLD", "1.0"))  # 1%
    NETWORK_PACKET_LOSS_WARNING_THRESHOLD: float = float(os.getenv("NETWORK_PACKET_LOSS_WARNING_THRESHOLD", "5.0"))  # 5%
    NETWORK_BANDWIDTH_GOOD_THRESHOLD: float = float(os.getenv("NETWORK_BANDWIDTH_GOOD_THRESHOLD", "80.0"))  # 80%
    NETWORK_BANDWIDTH_WARNING_THRESHOLD: float = float(os.getenv("NETWORK_BANDWIDTH_WARNING_THRESHOLD", "95.0"))  # 95%
    
    # Policy Engine Thresholds
    POLICY_DECISION_TIME_GOOD_THRESHOLD: float = float(os.getenv("POLICY_DECISION_TIME_GOOD_THRESHOLD", "1.0"))  # 1ms
    POLICY_DECISION_TIME_WARNING_THRESHOLD: float = float(os.getenv("POLICY_DECISION_TIME_WARNING_THRESHOLD", "10.0"))  # 10ms
    POLICY_EVALUATION_TIME_WARNING_THRESHOLD: float = float(os.getenv("POLICY_EVALUATION_TIME_WARNING_THRESHOLD", "100.0"))  # 100ms
    POLICY_EVALUATION_TIME_ERROR_THRESHOLD: float = float(os.getenv("POLICY_EVALUATION_TIME_ERROR_THRESHOLD", "1000.0"))  # 1000ms
    POLICY_COMPLEXITY_WARNING_THRESHOLD: int = int(os.getenv("POLICY_COMPLEXITY_WARNING_THRESHOLD", "10"))
    POLICY_RULES_MANY_THRESHOLD: int = int(os.getenv("POLICY_RULES_MANY_THRESHOLD", "20"))
    POLICY_RULES_SOME_THRESHOLD: int = int(os.getenv("POLICY_RULES_SOME_THRESHOLD", "10"))
    
    # Timeout Settings
    HTTP_CONNECT_TIMEOUT: float = float(os.getenv("HTTP_CONNECT_TIMEOUT", "10.0"))  # Increased
    HTTP_READ_TIMEOUT: float = float(os.getenv("HTTP_READ_TIMEOUT", "120.0"))  # Increased for better stability
    HTTP_WRITE_TIMEOUT: float = float(os.getenv("HTTP_WRITE_TIMEOUT", "30.0"))  # Increased
    HTTP_POOL_TIMEOUT: float = float(os.getenv("HTTP_POOL_TIMEOUT", "120.0"))  # Increased
    
    # Connection Pool Settings with keepalive
    MAX_KEEPALIVE_CONNECTIONS: int = int(os.getenv("MAX_KEEPALIVE_CONNECTIONS", "20"))  # Increased
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "50"))  # Increased
    KEEPALIVE_EXPIRY: float = float(os.getenv("KEEPALIVE_EXPIRY", "120.0"))  # Increased to 2 minutes
    
    # WebSocket and Polling Settings with better intervals
    WEBSOCKET_RECONNECT_DELAY: int = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "15"))  # Reduced for faster reconnect
    POLLING_INTERVAL: int = int(os.getenv("POLLING_INTERVAL", "10"))  # Reduced for more responsive updates
    OVERVIEW_UPDATE_INTERVAL: int = int(os.getenv("OVERVIEW_UPDATE_INTERVAL", "20"))  # Reduced
    FL_REFRESH_INTERVAL: int = int(os.getenv("FL_REFRESH_INTERVAL", "15"))  # Reduced
    
    # Cache and Data Management
    MAX_CLIENT_ERRORS_STORED: int = int(os.getenv("MAX_CLIENT_ERRORS_STORED", "20"))
    METRICS_CACHE_TTL: int = int(os.getenv("METRICS_CACHE_TTL", "10"))  # seconds
    
    class Config:
        """Pydantic configuration."""
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# Log the loaded settings for verification during startup
logger.info(f"=== MicroFed Dashboard API v{settings.APP_VERSION} ===")
logger.info(f"Build Date: {settings.BUILD_DATE}")
logger.info(f"Git Commit: {settings.GIT_COMMIT}")
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"Loaded GNS3_URL: {settings.GNS3_URL}")
logger.info(f"Loaded COLLECTOR_URL: {settings.COLLECTOR_URL}")
logger.info(f"Loaded POLICY_ENGINE_URL: {settings.POLICY_ENGINE_URL}")
logger.info(f"Connection Timeout: {settings.CONNECTION_TIMEOUT}s")
logger.info(f"Connection Retries: {settings.CONNECTION_RETRIES}")
logger.info(f"Loaded LOG_LEVEL: {settings.LOG_LEVEL}")
logger.info(f"Loaded SCENARIOS_DIR: {settings.SCENARIOS_DIR}")

# Create a thresholds object for easy access in templates
class DashboardThresholds:
    """Centralized dashboard thresholds configuration"""
    
    @property
    def fl_accuracy_thresholds(self) -> Dict[str, float]:
        return {
            "good": settings.FL_ACCURACY_GOOD_THRESHOLD,
            "warning": settings.FL_ACCURACY_WARNING_THRESHOLD
        }
    
    @property  
    def fl_loss_thresholds(self) -> Dict[str, float]:
        return {
            "good": settings.FL_LOSS_GOOD_THRESHOLD,
            "warning": settings.FL_LOSS_WARNING_THRESHOLD,
            "isHigherBetter": False
        }
    
    @property
    def network_latency_thresholds(self) -> Dict[str, float]:
        return {
            "good": settings.NETWORK_LATENCY_GOOD_THRESHOLD,
            "warning": settings.NETWORK_LATENCY_WARNING_THRESHOLD,
            "isHigherBetter": False
        }
    
    @property
    def network_packet_loss_thresholds(self) -> Dict[str, float]:
        return {
            "good": settings.NETWORK_PACKET_LOSS_GOOD_THRESHOLD,
            "warning": settings.NETWORK_PACKET_LOSS_WARNING_THRESHOLD,
            "isHigherBetter": False
        }
    
    @property
    def network_bandwidth_thresholds(self) -> Dict[str, float]:
        return {
            "good": settings.NETWORK_BANDWIDTH_GOOD_THRESHOLD,
            "warning": settings.NETWORK_BANDWIDTH_WARNING_THRESHOLD,
            "isHigherBetter": False
        }
    
    @property
    def policy_decision_time_thresholds(self) -> Dict[str, float]:
        return {
            "good": settings.POLICY_DECISION_TIME_GOOD_THRESHOLD,
            "warning": settings.POLICY_DECISION_TIME_WARNING_THRESHOLD,
            "isHigherBetter": False
        }

thresholds = DashboardThresholds()