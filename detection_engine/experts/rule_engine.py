# detection_engine/experts/rule_engine.py
from .base_expert import BaseExpert
from shared.schemas import ExpertDecision

class RuleEngineExpert(BaseExpert):
    def __init__(self):
        super().__init__("rule_engine", "rule_based")
        self.rules = self._load_rules()
    
    def _load_rules(self):
        return [
            {
                'name': 'high_amount',
                'condition': lambda t: t.amount > 1000,
                'weight': 0.7,
                'description': 'Transaction amount exceeds $1000'
            },
            {
                'name': 'new_location', 
                'condition': lambda t: self._is_new_location(t),
                'weight': 0.5,
                'description': 'Transaction from new geographic location'
            },
            {
                'name': 'velocity_anomaly',
                'condition': lambda t: self._check_velocity(t),
                'weight': 0.6,
                'description': 'Unusual transaction frequency'
            }
        ]
    
    def predict(self, transaction):
        score = 0.0
        triggered_rules = []
        
        for rule in self.rules:
            if rule['condition'](transaction):
                score += rule['weight']
                triggered_rules.append(rule)
        
        # Normalize score
        score = min(1.0, score)
        
        factors = []
        for rule in triggered_rules:
            factors.append({
                'description': rule['description'],
                'impact': rule['weight'],
                'features_involved': ['rule_based']
            })
        
        return ExpertDecision(
            expert_name=self.name,
            score=score,
            confidence=1.0,  # Rules are deterministic
            contributing_factors=factors,
            model_type=self.model_type
        )
    
    def _is_new_location(self, transaction):
        # Mock location check
        return hash(transaction.location) % 10 == 0  # 10% chance
    
    def _check_velocity(self, transaction):
        # Mock velocity check  
        return hash(transaction.customer_id + transaction.timestamp.isoformat()) % 5 == 0