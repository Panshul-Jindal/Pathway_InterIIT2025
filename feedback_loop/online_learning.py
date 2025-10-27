# feedback_loop/online_learning.py
from shared.schemas import Feedback
from shared.redis_client import redis_client
import json
import asyncio
from typing import Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OnlineLearningManager:
    def __init__(self):
        self.learning_rate = 0.1
        self.batch_size = 10
        self.pending_updates = []
        
        # Performance tracking per expert
        self.expert_stats = {}
    
    async def update_models(self, feedback: Feedback):
        """Update online learning models with feedback"""
        logger.info(f"🔄 Online learning: Queuing feedback for {feedback.alert_id}")
        
        # Add to pending updates
        self.pending_updates.append(feedback)
        
        # Process batch if we have enough samples
        if len(self.pending_updates) >= self.batch_size:
            await self._process_batch_update()
    
    async def _process_batch_update(self):
        """Process a batch of feedback updates"""
        if not self.pending_updates:
            return
        
        logger.info(f"🔄 Processing batch of {len(self.pending_updates)} feedback samples")
        
        try:
            # **FIX 1: Aggregate performance metrics with importance weighting**
            expert_performance = {}
            
            for feedback in self.pending_updates:
                # Get feedback metadata (includes importance weight)
                metadata = await self._get_feedback_metadata(feedback.alert_id)
                
                if not metadata:
                    logger.warning(f"No metadata for {feedback.alert_id}")
                    continue
                
                original_decisions = metadata.get('original_decisions', {})
                importance_weight = metadata.get('importance_weight', 1.0)
                
                # Evaluate each expert's performance
                for expert_name, decision in original_decisions.items():
                    if expert_name not in expert_performance:
                        expert_performance[expert_name] = {
                            'correct': 0.0,
                            'total': 0.0,
                            'weighted_correct': 0.0,
                            'weighted_total': 0.0,
                            'scores': []
                        }
                    
                    # Check if expert was correct
                    expert_predicted_fraud = decision['score'] > 0.5
                    was_correct = expert_predicted_fraud == feedback.correct_label
                    
                    # **FIX 2: Apply importance weighting**
                    expert_performance[expert_name]['total'] += 1
                    expert_performance[expert_name]['weighted_total'] += importance_weight
                    
                    if was_correct:
                        expert_performance[expert_name]['correct'] += 1
                        expert_performance[expert_name]['weighted_correct'] += importance_weight
                    
                    expert_performance[expert_name]['scores'].append({
                        'score': decision['score'],
                        'correct': was_correct,
                        'weight': importance_weight
                    })
            
            # **FIX 3: Calculate weighted accuracy and publish updates**
            if expert_performance:
                await self._update_expert_weights(expert_performance)
                await self._persist_statistics(expert_performance)
            
            # Clear processed batch
            self.pending_updates = []
            
        except Exception as e:
            logger.error(f"Error processing batch update: {e}")
    
    async def _get_feedback_metadata(self, alert_id: str):
        """Retrieve feedback metadata from Redis"""
        try:
            data = await redis_client.get(f"feedback_metadata:{alert_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting feedback metadata: {e}")
        return None
    
    async def _update_expert_weights(self, performance: Dict):
        """
        Update expert weights based on weighted performance
        Publishes to 'weight_updates' channel for detection engine
        """
        weights_update = {}
        
        for expert_name, stats in performance.items():
            weighted_total = stats['weighted_total']
            
            if weighted_total > 0:
                # Calculate weighted accuracy
                weighted_accuracy = stats['weighted_correct'] / weighted_total
                
                # **FIX 4: Exponential moving average for stability**
                if expert_name in self.expert_stats:
                    old_accuracy = self.expert_stats[expert_name].get('accuracy', 0.5)
                    # Smooth update: new = alpha * new + (1-alpha) * old
                    weighted_accuracy = (
                        self.learning_rate * weighted_accuracy + 
                        (1 - self.learning_rate) * old_accuracy
                    )
                
                weights_update[expert_name] = weighted_accuracy
                
                # Update internal stats
                self.expert_stats[expert_name] = {
                    'accuracy': weighted_accuracy,
                    'total_samples': stats['total'],
                    'weighted_samples': weighted_total,
                    'last_update': datetime.now().isoformat()
                }
        
        # **FIX 5: Publish weight updates to detection engine**
        if weights_update:
            await redis_client.publish(
                'weight_updates',
                json.dumps(weights_update)
            )
            logger.info(f"📊 Published weight updates: {weights_update}")
    
    async def _persist_statistics(self, performance: Dict):
        """Persist expert performance statistics to Redis"""
        try:
            stats_data = {
                'timestamp': datetime.now().isoformat(),
                'performance': performance,
                'expert_stats': self.expert_stats
            }
            
            await redis_client.setex(
                'online_learning_stats',
                3600,  # 1 hour TTL
                json.dumps(stats_data, default=str)
            )
            
            logger.info("💾 Persisted online learning statistics")
            
        except Exception as e:
            logger.error(f"Error persisting statistics: {e}")
    
    async def get_expert_statistics(self) -> Dict:
        """Get current expert performance statistics"""
        return {
            'expert_stats': self.expert_stats,
            'pending_updates': len(self.pending_updates),
            'batch_size': self.batch_size,
            'learning_rate': self.learning_rate
        }