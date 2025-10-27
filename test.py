# simple_test.py
import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

# Mock classes for testing
class MockTransaction:
    def __init__(self, transaction_id, amount, customer_id, features=None):
        self.transaction_id = transaction_id
        self.amount = amount
        self.customer_id = customer_id
        self.merchant_id = f"merch_{random.randint(1, 100)}"
        self.location = f"loc_{random.randint(1, 50)}"
        self.device_id = f"device_{random.randint(1, 10)}"
        self.transaction_type = "purchase"
        self.timestamp = datetime.now()
        self.features = features or {f"V{i}": random.uniform(-3, 3) for i in range(1, 10)}

class MockExpert:
    def __init__(self, name):
        self.name = name
    
    def predict(self, transaction):
        # Simple mock scoring
        base_score = transaction.amount / 5000  # Normalize by amount
        noise = random.uniform(-0.2, 0.2)
        score = max(0, min(1, base_score + noise))
        
        factors = [{
            'description': f'{self.name} detected pattern',
            'impact': score,
            'features_involved': ['amount', 'pattern']
        }]
        
        return {
            'expert_name': self.name,
            'score': score,
            'confidence': random.uniform(0.7, 0.95),
            'contributing_factors': factors,
            'model_type': 'mock'
        }

class SimpleDetectionEngine:
    def __init__(self):
        self.experts = {
            'xgboost': MockExpert('xgboost'),
            'lightgbm': MockExpert('lightgbm'), 
            'rule_engine': MockExpert('rule_engine'),
            'streaming_rf': MockExpert('streaming_rf')
        }
    
    def process_transaction(self, transaction):
        expert_decisions = {}
        
        for expert_name, expert in self.experts.items():
            expert_decisions[expert_name] = expert.predict(transaction)
        
        # Simple ensemble (average)
        final_score = sum(dec['score'] for dec in expert_decisions.values()) / len(expert_decisions)
        
        ensemble_decision = {
            'transaction_id': transaction.transaction_id,
            'final_score': final_score,
            'expert_decisions': expert_decisions,
            'weights': {name: 0.25 for name in expert_decisions},  # Equal weights
            'primary_factors': [{
                'description': f'Ensemble score: {final_score:.3f}',
                'impact': final_score,
                'experts': list(expert_decisions.keys())
            }],
            'needs_human_review': 0.3 <= final_score <= 0.7
        }
        
        return ensemble_decision

class SimpleExplanationService:
    def generate_explanation(self, ensemble_decision):
        score = ensemble_decision['final_score']
        
        if score > 0.7:
            risk = "HIGH"
            action = "BLOCK and verify"
        elif score > 0.4:
            risk = "MEDIUM" 
            action = "Require 2FA"
        else:
            risk = "LOW"
            action = "Allow with monitoring"
        
        return f"""
🚨 FRAUD ALERT

Transaction: {ensemble_decision['transaction_id']}
Risk Level: {risk} (Score: {score:.3f})
Recommended Action: {action}

Analysis by {len(ensemble_decision['expert_decisions'])} experts
"""

async def run_demo():
    print("🚀 Starting SentinelFlow Demo...")
    print("=" * 50)
    
    detection_engine = SimpleDetectionEngine()
    explanation_service = SimpleExplanationService()
    
    # Generate test transactions
    test_transactions = [
        MockTransaction(f"test_{i}", random.uniform(10, 2000), f"cust_{random.randint(1, 100)}")
        for i in range(10)
    ]
    
    for i, transaction in enumerate(test_transactions):
        print(f"\n📊 Processing Transaction {i+1}:")
        print(f"   Amount: ${transaction.amount:.2f}")
        print(f"   Customer: {transaction.customer_id}")
        
        # Detect fraud
        ensemble_decision = detection_engine.process_transaction(transaction)
        
        # Generate explanation
        explanation = explanation_service.generate_explanation(ensemble_decision)
        
        print(explanation)
        
        # Simulate processing delay
        await asyncio.sleep(1)
    
    print("\n" + "=" * 50)
    print("✅ Demo completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_demo())