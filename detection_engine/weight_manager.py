# detection_engine/weight_manager.py
import numpy as np
from collections import deque, defaultdict
from typing import Dict, List
import math
import logging

logger = logging.getLogger(__name__)


class ContextualBanditWeightManager:
    def __init__(self, experts: List[str], context_dim: int, alpha: float = 0.1):
        self.experts = experts
        self.context_dim = context_dim
        self.alpha = alpha
        
        # LinUCB for each expert
        self.bandits = {
            expert: LinUCB(context_dim, alpha) 
            for expert in experts
        }
        
        self.performance_tracker = ExpertPerformanceTracker(experts)
        
    def select_experts(self, context: List[float]) -> Dict[str, float]:
        """Select expert weights using contextual bandits"""
        # Ensure context is correct dimension
        context_vector = np.array(context)
        if len(context_vector) != self.context_dim:
            # Pad or truncate to match dimension
            if len(context_vector) < self.context_dim:
                context_vector = np.pad(
                    context_vector, 
                    (0, self.context_dim - len(context_vector))
                )
            else:
                context_vector = context_vector[:self.context_dim]
        
        # Get UCB scores for each expert
        ucb_scores = {}
        for expert, bandit in self.bandits.items():
            ucb_scores[expert] = bandit.ucb_score(context_vector)
        
        # Softmax to get probabilities
        return self._softmax_normalize(ucb_scores)
    
    def update_with_feedback(self, context: List[float], expert_decisions: Dict, 
                           true_label: bool, importance_weight: float = 1.0):
        """
        Update bandits with delayed feedback
        
        Args:
            context: Feature vector describing the transaction context
            expert_decisions: Dictionary of expert decisions (can be dict or ExpertDecision objects)
            true_label: True if transaction was fraud, False if legitimate
            importance_weight: Weight to apply based on feedback delay
        """
        # Ensure context is correct dimension
        context_vector = np.array(context)
        if len(context_vector) != self.context_dim:
            if len(context_vector) < self.context_dim:
                context_vector = np.pad(
                    context_vector, 
                    (0, self.context_dim - len(context_vector))
                )
            else:
                context_vector = context_vector[:self.context_dim]
        
        for expert_name, decision in expert_decisions.items():
            if expert_name in self.bandits:
                # Handle both dict and ExpertDecision objects
                if isinstance(decision, dict):
                    expert_score = decision.get('score', 0.5)
                else:
                    expert_score = decision.score
                
                # Calculate reward based on expert performance
                reward = self._calculate_reward(expert_score, true_label)
                weighted_reward = reward * importance_weight
                
                # Update bandit
                self.bandits[expert_name].update(context_vector, weighted_reward)
                
                # Update performance tracker
                self.performance_tracker.update(expert_name, reward)
        
        logger.debug(f"Updated bandits with feedback (weight: {importance_weight:.3f})")
    
    def _calculate_reward(self, expert_score: float, true_label: bool) -> float:
        """
        Calculate reward for expert prediction
        
        Reward is higher when:
        - Expert correctly predicts fraud (high score when true_label=True)
        - Expert correctly predicts legitimate (low score when true_label=False)
        """
        if true_label:  # Actual fraud
            return expert_score  # Higher score for fraud = better
        else:  # Legitimate transaction
            return 1.0 - expert_score  # Lower score for legitimate = better
    
    def _softmax_normalize(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Convert scores to probability distribution"""
        # Add temperature parameter for exploration
        temperature = 1.0
        
        exp_scores = {k: math.exp(v / temperature) for k, v in scores.items()}
        total = sum(exp_scores.values())
        
        if total == 0:
            # Uniform distribution if all scores are -inf
            return {k: 1.0 / len(scores) for k in scores.keys()}
        
        return {k: v / total for k, v in exp_scores.items()}
    
    def get_expert_statistics(self) -> Dict:
        """Get current statistics for all experts"""
        stats = {}
        for expert_name in self.experts:
            recent_perf = self.performance_tracker.get_recent_performance(expert_name)
            stats[expert_name] = {
                'recent_performance': recent_perf,
                'theta': self.bandits[expert_name].theta.tolist(),
                'confidence': self.bandits[expert_name].get_confidence()
            }
        return stats


class LinUCB:
    """Linear Upper Confidence Bound algorithm"""
    def __init__(self, context_dim: int, alpha: float = 0.1):
        self.context_dim = context_dim
        self.A = np.eye(context_dim)  # Context covariance matrix
        self.b = np.zeros(context_dim)  # Reward vector
        self.alpha = alpha
        self.theta = np.zeros(context_dim)  # Model parameters
        self.n_updates = 0
    
    def ucb_score(self, context: np.ndarray) -> float:
        """Calculate UCB score for context"""
        context = context.flatten()
        
        # Mean prediction
        mean = self.theta.dot(context)
        
        # Confidence bound
        try:
            A_inv = np.linalg.inv(self.A)
            confidence = self.alpha * np.sqrt(
                context.dot(A_inv).dot(context)
            )
        except np.linalg.LinAlgError:
            # If matrix is singular, use small confidence
            confidence = self.alpha * 0.1
        
        return mean + confidence
    
    def update(self, context: np.ndarray, reward: float):
        """Update model with new observation"""
        context = context.flatten()
        
        # Update matrices
        self.A += np.outer(context, context)
        self.b += reward * context
        
        # Update parameters
        try:
            self.theta = np.linalg.inv(self.A).dot(self.b)
        except np.linalg.LinAlgError:
            # If inversion fails, use regularization
            regularization = 0.01 * np.eye(self.context_dim)
            self.theta = np.linalg.inv(self.A + regularization).dot(self.b)
        
        self.n_updates += 1
    
    def get_confidence(self) -> float:
        """Get overall confidence in predictions"""
        # Higher updates = higher confidence
        return min(1.0, self.n_updates / 100.0)


class ExpertPerformanceTracker:
    """Track expert performance over time"""
    def __init__(self, experts: List[str], window_size: int = 1000):
        self.performance_history = {
            expert: deque(maxlen=window_size) 
            for expert in experts
        }
        self.window_size = window_size
    
    def update(self, expert: str, reward: float):
        """Record new performance observation"""
        if expert in self.performance_history:
            self.performance_history[expert].append(reward)
    
    def get_recent_performance(self, expert: str, window: int = 100) -> float:
        """Get recent performance (moving average)"""
        if expert not in self.performance_history:
            return 0.5  # Neutral prior
        
        history = list(self.performance_history[expert])
        if len(history) == 0:
            return 0.5  # Neutral prior
        
        if len(history) < window:
            recent = history
        else:
            recent = history[-window:]
        
        return np.mean(recent)
    
    def get_all_statistics(self) -> Dict:
        """Get statistics for all experts"""
        stats = {}
        for expert in self.performance_history.keys():
            history = list(self.performance_history[expert])
            if history:
                stats[expert] = {
                    'mean': np.mean(history),
                    'std': np.std(history),
                    'count': len(history),
                    'recent_mean': self.get_recent_performance(expert, 100)
                }
            else:
                stats[expert] = {
                    'mean': 0.5,
                    'std': 0.0,
                    'count': 0,
                    'recent_mean': 0.5
                }
        return stats