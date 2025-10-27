# detection_engine/experts/streaming_rf.py
import numpy as np
from .base_expert import BaseExpert
from shared.schemas import ExpertDecision
from collections import deque
import random

class StreamingRFExpert(BaseExpert):
    def __init__(self, window_size=1000, n_estimators=10):
        super().__init__("streaming_rf", "streaming")
        self.window_size = window_size
        self.n_estimators = n_estimators
        self.data_window = deque(maxlen=window_size)
        self.label_window = deque(maxlen=window_size)
        self.models = []  # In production, use actual streaming RF
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize simple streaming models"""
        # For prototype, we'll use simple rules that adapt
        self.rules = [
            {'feature': 'amount', 'threshold': 1000, 'weight': 0.7},
            {'feature': 'velocity', 'threshold': 10, 'weight': 0.6},
            {'feature': 'location_risk', 'threshold': 0.8, 'weight': 0.5}
        ]
    
    def predict(self, transaction):
        features = self._extract_features(transaction)
        
        # Update data window
        self.data_window.append(features)
        
        # Calculate score based on adaptive rules
        score = self._calculate_streaming_score(transaction, features)
        
        factors = []
        for rule in self.rules:
            factor_value = self._get_feature_value