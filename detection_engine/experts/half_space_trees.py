# detection_engine/experts/half_space_trees.py
import numpy as np
from .base_expert import BaseExpert
from shared.schemas import ExpertDecision
from collections import deque
import random

class HalfSpaceTreesExpert(BaseExpert):
    def __init__(self, window_size=1000, n_trees=25):
        super().__init__("half_space_trees", "streaming_anomaly")
        self.window_size = window_size
        self.n_trees = n_trees
        self.trees = []
        self.reference_window = deque(maxlen=window_size)
        self._initialize_trees()
        
    def _initialize_trees(self):
        """Initialize Half-Space Trees"""
        for _ in range(self.n_trees):
            tree = {
                'left_mass': 0,
                'right_mass': 0,
                'split_feature': None,
                'split_value': None
            }
            self.trees.append(tree)
    
    def predict(self, transaction):
        features = self._extract_features(transaction)
        
        # Update reference window
        self.reference_window.append(features)
        
        # Score transaction using Half-Space Trees
        score = self._calculate_anomaly_score(features)
        
        factors = [{
            'description': f'Half-Space Trees anomaly detection',
            'impact': score,
            'features_involved': ['composite_anomaly']
        }]
        
        return ExpertDecision(
            expert_name=self.name,
            score=score,
            confidence=min(1.0, abs(score) * 2),
            contributing_factors=factors,
            model_type=self.model_type
        )
    
    def _extract_features(self, transaction):
        """Extract numerical features from transaction"""
        feature_values = list(transaction.features.values())
        # Add engineered features
        feature_values.extend([
            transaction.amount / 1000,
            len(transaction.customer_id) / 100,
            hash(transaction.merchant_id) % 100 / 100
        ])
        return np.array(feature_values)
    
    def _calculate_anomaly_score(self, features):
        """Calculate anomaly score using Half-Space Trees principle"""
        if len(self.reference_window) < 10:
            return 0.1  # Not enough data
        
        # Simple mass-based anomaly detection
        # Points in sparse regions are more anomalous
        distances = []
        for ref_point in list(self.reference_window)[-100:]:  # Recent points
            distance = np.linalg.norm(features - ref_point)
            distances.append(distance)
        
        # Normalize distance to [0, 1] range
        if distances:
            avg_distance = np.mean(distances)
            max_distance = np.max(distances) if len(distances) > 1 else 1.0
            score = min(1.0, avg_distance / max_distance if max_distance > 0 else 0)
        else:
            score = 0.1
        
        return score
    
    def update(self, transaction, true_label):
        """Update model with new labeled data"""
        # Half-Space Trees don't typically update with labels
        # But we can adjust based on feedback
        pass