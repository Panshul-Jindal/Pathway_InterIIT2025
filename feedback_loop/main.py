# feedback_loop/main.py
import asyncio
import json
from shared.redis_client import redis_client
from shared.schemas import Feedback
from .delayed_feedback import DelayedFeedbackHandler
from .online_learning import OnlineLearningManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedbackLoop:
    def __init__(self):
        self.feedback_handler = DelayedFeedbackHandler()
        self.learning_manager = OnlineLearningManager()
        self.feedback_buffer = []
        self.buffer_size = 10
    
    async def start(self):
        """Start all feedback loop tasks"""
        logger.info("🔄 Starting Feedback Loop Service...")
        
        await asyncio.gather(
            self.process_feedback_stream(),
            self.periodic_batch_update()
        )
    
    async def process_feedback_stream(self):
        """Main loop for processing feedback"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('feedback')
        
        logger.info("👂 Feedback Loop listening for analyst feedback...")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    feedback_data = json.loads(message['data'])
                    feedback = Feedback(**feedback_data)
                    
                    # Add to buffer
                    self.feedback_buffer.append(feedback)
                    
                    # **FIX 1: Process delayed feedback with proper timing**
                    await self.feedback_handler.process_feedback(feedback)
                    
                    # **FIX 2: Trigger batch update if buffer is full**
                    if len(self.feedback_buffer) >= self.buffer_size:
                        await self.process_batch()
                    
                    logger.info(f"📊 Processed feedback for alert {feedback.alert_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing feedback: {e}")
    
    async def process_batch(self):
        """Process accumulated feedback as a batch"""
        if not self.feedback_buffer:
            return
        
        logger.info(f"🔄 Processing batch of {len(self.feedback_buffer)} feedback items")
        
        try:
            # Update online learning models
            for feedback in self.feedback_buffer:
                await self.learning_manager.update_models(feedback)
            
            # Trigger batch weight update
            await self.learning_manager._process_batch_update()
            
            # Clear buffer
            self.feedback_buffer = []
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
    
    async def periodic_batch_update(self):
        """Periodic batch updates even if buffer not full"""
        while True:
            await asyncio.sleep(60)  # Every minute
            
            if self.feedback_buffer:
                logger.info("⏰ Triggered periodic batch update")
                await self.process_batch()


if __name__ == "__main__":
    feedback_loop = FeedbackLoop()
    asyncio.run(feedback_loop.start())