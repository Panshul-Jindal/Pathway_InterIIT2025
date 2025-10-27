# shared/config.py
import os

class Config:
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Services
    DETECTION_ENGINE_URL = os.getenv('DETECTION_ENGINE_URL', 'http://localhost:8000')
    EXPLANATION_SERVICE_URL = os.getenv('EXPLANATION_SERVICE_URL', 'http://localhost:8001')
    DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8002')
    
    # Model paths
    KAGGLE_DATASET_PATH = os.getenv('KAGGLE_DATASET_PATH', 'data/kaggle_creditcard.csv')
    
    # Feature engineering
    VELOCITY_WINDOW_HOURS = 24
    AMOUNT_THRESHOLDS = [100, 500, 1000, 5000]