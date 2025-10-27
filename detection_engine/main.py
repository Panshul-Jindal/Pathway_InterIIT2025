# detection_engine/main.py
import asyncio
import pathway as pw
from pathway.stdlib.ml.index import KNNIndex
from .pathway_pipeline import build_fraud_pipeline
from .experts import (
    XGBoostExpert,
    LightGBMExpert, 
    RuleEngineExpert,
    StreamingRFExpert,
    HalfSpaceTreesExpert
)
from .weight_manager import ContextualBanditWeightManager
from shared.redis_client import redis_client
from shared.schemas import Transaction, EnsembleDecision
import json
import time
from typing import Dict, List

class DetectionEngine:
    def __init__(self):
        self.experts = {
            'xgboost': XGBoostExpert(),
            'lightgbm': LightGBMExpert(),
            'rule_engine': RuleEngineExpert(),
            'streaming_rf': StreamingRFExpert(),
            'half_space': HalfSpaceTreesExpert()
        }
        
        self.weight_manager = ContextualBanditWeightManager(
            list(self.experts.keys()),
            context_dim=10
        )
        
        # Build Pathway pipeline
        self.pipeline = build_fraud_pipeline(self.experts, self.weight_manager)
        
        # Kill switch state
        self.kill_switch_active = False
        
    async def start(self):
        """Start all background tasks"""
        print("🚀 Starting Detection Engine...")
        
        # Start concurrent tasks
        await asyncio.gather(
            self.process_transaction_stream(),
            self.listen_for_feedback(),
            self.listen_for_weight_updates(),
            self.listen_for_kill_switch()
        )
        
    async def process_transaction_stream(self):
        """Main processing loop for transaction stream"""
        print("📊 Transaction processing started")
        
        # Simulate transaction stream from Kaggle dataset
        transactions = self.simulate_kaggle_stream()
        
        for transaction in transactions:
            # Check kill switch
            if self.kill_switch_active:
                print("🛑 Kill switch active - skipping transaction processing")
                await asyncio.sleep(1)
                continue
            
            start_time = time.time()
            
            try:
                # Get expert predictions with explanations
                expert_decisions = {}
                for expert_name, expert in self.experts.items():
                    expert_decisions[expert_name] = expert.predict(transaction)
                
                # Get context-aware weights
                context = self.extract_context(transaction)
                weights = self.weight_manager.select_experts(context)
                
                # Ensemble decision
                ensemble_score = self.combine_predictions(expert_decisions, weights)
                
                # Build rich context for explanation
                ensemble_decision = EnsembleDecision(
                    transaction_id=transaction.transaction_id,
                    final_score=ensemble_score,
                    expert_decisions=expert_decisions,
                    weights=weights,
                    primary_factors=self.identify_primary_factors(expert_decisions),
                    needs_human_review=0.3 <= ensemble_score <= 0.7
                )
                
                # **FIX 1: Store decisions in Redis for feedback loop**
                await redis_client.setex(
                    f"decisions:{transaction.transaction_id}",
                    86400,  # 24 hour TTL
                    json.dumps({
                        k: v.dict() for k, v in expert_decisions.items()
                    })
                )
                
                # **FIX 2: Store transaction for feedback correlation**
                await redis_client.setex(
                    f"transaction:{transaction.transaction_id}",
                    86400,
                    json.dumps(transaction.dict(), default=str)
                )
                
                # Publish alert to Redis for explanation service
                alert_data = {
                    'transaction': transaction.dict(),
                    'ensemble_decision': ensemble_decision.dict(),
                    'processing_time': time.time() - start_time
                }
                
                await redis_client.publish('alerts', json.dumps(alert_data, default=str))
                
                print(f"✅ Processed {transaction.transaction_id} - Score: {ensemble_score:.3f}")
                
            except Exception as e:
                print(f"❌ Error processing transaction {transaction.transaction_id}: {e}")
            
            # Simulate streaming delay
            await asyncio.sleep(0.1)
    
    async def listen_for_feedback(self):
        """Listen for real-time feedback from dashboard"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('feedback')
        
        print("👂 Listening for analyst feedback...")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    feedback_data = json.loads(message['data'])
                    await self.process_feedback(feedback_data)
                except Exception as e:
                    print(f"❌ Error processing feedback: {e}")
    
    async def process_feedback(self, feedback_data: Dict):
        """Process feedback and update weights immediately"""
        alert_id = feedback_data['alert_id']
        correct_label = feedback_data['correct_label']
        
        # Get stored transaction and decisions
        transaction_data = await redis_client.get(f"transaction:{alert_id}")
        decisions_data = await redis_client.get(f"decisions:{alert_id}")
        
        if not transaction_data or not decisions_data:
            print(f"⚠️ Missing data for alert {alert_id}")
            return
        
        # Reconstruct transaction and decisions
        transaction = Transaction(**json.loads(transaction_data))
        expert_decisions = json.loads(decisions_data)
        
        # Extract context
        context = self.extract_context(transaction)
        
        # **FIX 3: Update contextual bandit with feedback**
        self.weight_manager.update_with_feedback(
            context,
            expert_decisions,
            correct_label,
            importance_weight=1.0
        )
        
        print(f"🔄 Updated weights from feedback for alert {alert_id}")
    
    async def listen_for_weight_updates(self):
        """Listen for batch weight updates from feedback loop"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('weight_updates')
        
        print("👂 Listening for weight updates...")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    weight_updates = json.loads(message['data'])
                    await self.apply_weight_updates(weight_updates)
                except Exception as e:
                    print(f"❌ Error applying weight updates: {e}")
    
    async def apply_weight_updates(self, weight_updates: Dict):
        """Apply batch weight updates from online learning"""
        print(f"🔄 Applying batch weight updates: {weight_updates}")
        
        # Update bandit performance tracking
        for expert_name, performance_score in weight_updates.items():
            if expert_name in self.weight_manager.performance_tracker.performance_history:
                # Update performance tracker
                self.weight_manager.performance_tracker.update(
                    expert_name, 
                    performance_score
                )
        
        print("✅ Weight updates applied")
    
    async def listen_for_kill_switch(self):
        """Listen for kill switch commands from dashboard"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('kill_switch')
        
        print("👂 Listening for kill switch...")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    command = json.loads(message['data'])
                    self.kill_switch_active = command.get('active', False)
                    
                    if self.kill_switch_active:
                        print("🛑 KILL SWITCH ACTIVATED - Pausing detections")
                    else:
                        print("✅ Kill switch deactivated - Resuming detections")
                        
                except Exception as e:
                    print(f"❌ Error processing kill switch: {e}")
    
    def extract_context(self, transaction: Transaction) -> List[float]:
        """Extract context for bandit decision"""
        # Build 10-dimensional context vector
        context = [
            transaction.amount / 1000,  # Normalized amount
            len(transaction.customer_id) % 100 / 100,  # Customer feature
            hash(transaction.merchant_id) % 100 / 100,  # Merchant risk
            hash(transaction.location) % 100 / 100,  # Location risk
            hash(transaction.device_id) % 100 / 100,  # Device risk
            transaction.timestamp.hour / 24,  # Time of day
            transaction.timestamp.weekday() / 7,  # Day of week
            len(transaction.features) / 30,  # Feature dimensionality
            sum(abs(v) for v in transaction.features.values()) / 100,  # Feature magnitude
            1.0 if transaction.transaction_type == "purchase" else 0.0  # Transaction type
        ]
        
        return context[:10]  # Ensure exactly 10 dimensions
    
    def combine_predictions(self, expert_decisions: Dict, weights: Dict) -> float:
        """Weighted ensemble combination"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for expert_name, decision in expert_decisions.items():
            weight = weights.get(expert_name, 0.0)
            weighted_sum += decision.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def identify_primary_factors(self, expert_decisions: Dict) -> List[Dict]:
        """Identify cross-expert important factors"""
        factor_scores = {}
        
        for expert_name, decision in expert_decisions.items():
            for factor in decision.contributing_factors:
                key = factor['description']
                if key not in factor_scores:
                    factor_scores[key] = {'impact': 0.0, 'experts': []}
                factor_scores[key]['impact'] += abs(factor['impact'])
                factor_scores[key]['experts'].append(expert_name)
        
        # Return top 3 factors
        sorted_factors = sorted(
            [{'description': k, **v} for k, v in factor_scores.items()],
            key=lambda x: x['impact'],
            reverse=True
        )[:3]
        
        return sorted_factors
    
    def simulate_kaggle_stream(self):
        """Simulate streaming from Kaggle dataset"""
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Load Kaggle credit card fraud dataset
        try:
            df = pd.read_csv('data/kaggle_creditcard.csv')
        except FileNotFoundError:
            print("⚠️ Kaggle dataset not found, using mock data")
            df = self._generate_mock_data()
        
        base_time = datetime.now()
        
        for idx, row in df.iterrows():
            # Create realistic timestamps
            timestamp = base_time + timedelta(seconds=idx * 10)
            
            transaction = Transaction(
                transaction_id=f"txn_{idx}",
                timestamp=timestamp,
                amount=float(row.get('Amount', np.random.uniform(10, 5000))),
                customer_id=f"cust_{hash(str(row.get('Time', idx))) % 1000}",
                merchant_id=f"merch_{hash(str(row)) % 100}",
                location=f"loc_{np.random.randint(1, 50)}",
                device_id=f"device_{np.random.randint(1, 10)}",
                transaction_type="purchase",
                features={f"V{i}": float(row.get(f"V{i}", np.random.randn())) 
                         for i in range(1, 29)}
            )
            yield transaction
    
    def _generate_mock_data(self):
        """Generate mock data if Kaggle dataset not available"""
        import pandas as pd
        import numpy as np
        
        n_samples = 1000
        data = {
            'Amount': np.random.lognormal(4, 2, n_samples),
            'Time': range(n_samples)
        }
        
        # Add V1-V28 features
        for i in range(1, 29):
            data[f'V{i}'] = np.random.randn(n_samples)
        
        return pd.DataFrame(data)

if __name__ == "__main__":
    engine = DetectionEngine()
    asyncio.run(engine.start())