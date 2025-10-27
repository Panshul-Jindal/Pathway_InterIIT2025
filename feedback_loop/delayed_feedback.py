# feedback_loop/delayed_feedback.py
import asyncio
from typing import Dict
from shared.schemas import Feedback, Transaction
from shared.redis_client import redis_client
import time
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DelayedFeedbackHandler:
    def __init__(self):
        self.delay_distribution = DelayDistributionEstimator()
        
    async def process_feedback(self, feedback: Feedback):
        """Process feedback with delay handling"""
        try:
            # **FIX 1: Get the original transaction to calculate real delay**
            transaction_data = await redis_client.get(
                f"transaction:{feedback.alert_id}"
            )
            
            if not transaction_data:
                logger.warning(f"⚠️ No transaction found for alert {feedback.alert_id}")
                return
            
            transaction = Transaction(**json.loads(transaction_data))
            
            # **FIX 2: Calculate actual delay from transaction timestamp**
            delay_hours = self._calculate_actual_delay(
                transaction.timestamp,
                feedback.feedback_timestamp
            )
            
            # Get original expert decisions
            original_decisions = await self._get_original_decisions(feedback.alert_id)
            
            if not original_decisions:
                logger.warning(f"⚠️ No original decisions found for alert {feedback.alert_id}")
                return
            
            # **FIX 3: Calculate importance weight based on actual delay**
            importance_weight = self.delay_distribution.calculate_importance_weight(
                delay_hours
            )
            
            # **FIX 4: Store feedback with metadata in Redis**
            feedback_metadata = {
                'feedback': feedback.dict(),
                'original_decisions': original_decisions,
                'importance_weight': importance_weight,
                'delay_hours': delay_hours,
                'transaction_timestamp': transaction.timestamp.isoformat(),
                'processed_timestamp': datetime.now().isoformat()
            }
            
            await redis_client.setex(
                f"feedback_metadata:{feedback.alert_id}",
                86400,  # 24 hour TTL
                json.dumps(feedback_metadata, default=str)
            )
            
            # Update delay distribution
            self.delay_distribution.record_delay(delay_hours)
            
            logger.info(
                f"📊 Processed feedback with {delay_hours:.2f}h delay, "
                f"importance weight: {importance_weight:.3f}"
            )
            
        except Exception as e:
            logger.error(f"Error processing delayed feedback: {e}")
    
    async def _get_original_decisions(self, alert_id: str):
        """Retrieve original expert decisions for an alert"""
        try:
            data = await redis_client.get(f"decisions:{alert_id}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving decisions: {e}")
            return None
    
    def _calculate_actual_delay(self, transaction_time: datetime, 
                               feedback_time: datetime) -> float:
        """Calculate feedback delay in hours"""
        try:
            if isinstance(transaction_time, str):
                transaction_time = datetime.fromisoformat(transaction_time)
            if isinstance(feedback_time, str):
                feedback_time = datetime.fromisoformat(feedback_time)
            
            delta = feedback_time - transaction_time
            delay_hours = delta.total_seconds() / 3600
            
            return max(0.0, delay_hours)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Error calculating delay: {e}")
            return 1.0  # Default to 1 hour
    
    async def get_feedback_statistics(self) -> Dict:
        """Get statistics about feedback delays"""
        return {
            'mean_delay': self.delay_distribution.get_mean_delay(),
            'total_feedbacks': len(self.delay_distribution.delays),
            'delay_histogram': self.delay_distribution.get_histogram()
        }


class DelayDistributionEstimator:
    """Estimate delay distribution for importance weighting"""
    
    def __init__(self):
        self.delays = []
        self.max_history = 10000
        
    def record_delay(self, delay_hours: float):
        """Record a new delay observation"""
        self.delays.append(delay_hours)
        
        # Keep only recent history
        if len(self.delays) > self.max_history:
            self.delays = self.delays[-self.max_history:]
    
    def calculate_importance_weight(self, delay_hours: float) -> float:
        """
        Calculate importance weight using inverse propensity scoring
        
        Longer delays get lower weights because:
        1. Patterns may have changed
        2. Context may be different
        3. Less relevant for current model
        """
        # Exponential decay: weight = exp(-lambda * delay)
        decay_rate = 0.1  # Adjust based on your fraud domain
        weight = 2.718 ** (-decay_rate * delay_hours)
        
        # Ensure minimum weight for very old feedback
        min_weight = 0.1
        return max(min_weight, weight)
    
    def get_mean_delay(self) -> float:
        """Get mean delay from recent feedback"""
        if not self.delays:
            return 0.0
        return sum(self.delays) / len(self.delays)
    
    def get_histogram(self, bins: int = 5) -> Dict:
        """Get delay distribution histogram"""
        if not self.delays:
            return {}
        
        max_delay = max(self.delays)
        bin_size = max_delay / bins if max_delay > 0 else 1
        
        histogram = {}
        for delay in self.delays:
            bin_idx = min(int(delay / bin_size), bins - 1)
            bin_label = f"{bin_idx * bin_size:.1f}-{(bin_idx + 1) * bin_size:.1f}h"
            histogram[bin_label] = histogram.get(bin_label, 0) + 1
        
        return histogram