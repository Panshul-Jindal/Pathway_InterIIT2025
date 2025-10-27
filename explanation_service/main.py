# explanation_service/main.py
from fastapi import FastAPI
import asyncio
import json
from .explanation_generator import ExplanationGenerator
from shared.redis_client import redis_client
from shared.schemas import Alert
import logging

app = FastAPI(title="SentinelFlow Explanation Service")

class ExplanationOrchestrator:
    """
    Orchestrator that decides between template and LLM explanations
    Based on confidence level and complexity
    """
    def __init__(self, generator: ExplanationGenerator):
        self.generator = generator
        
    async def route_explanation(self, alert_data: dict) -> dict:
        """
        Route to appropriate explanation method based on:
        - Confidence level (high confidence → template)
        - Ambiguity (medium scores → LLM)
        - Complexity (number of conflicting experts)
        """
        ensemble_decision = alert_data['ensemble_decision']
        final_score = ensemble_decision['final_score']
        expert_decisions = ensemble_decision['expert_decisions']
        
        # Analyze decision characteristics
        is_high_confidence = final_score > 0.8 or final_score < 0.2
        is_ambiguous = 0.3 <= final_score <= 0.7
        has_expert_conflict = self._check_expert_conflict(expert_decisions)
        
        # Decision logic
        if is_high_confidence and not has_expert_conflict:
            # Simple case: use fast template
            explanation_type = "template"
            explanation = self.generator._generate_template_explanation(ensemble_decision)
            
        elif is_ambiguous or has_expert_conflict:
            # Complex case: use LLM for nuanced explanation
            explanation_type = "llm"
            explanation = await self.generator._generate_gemini_explanation(ensemble_decision)
            
        else:
            # Default to template
            explanation_type = "template"
            explanation = self.generator._generate_template_explanation(ensemble_decision)
        
        # Add metadata about routing decision
        return {
            'explanation': explanation,
            'explanation_type': explanation_type,
            'routing_reason': self._get_routing_reason(
                is_high_confidence, 
                is_ambiguous, 
                has_expert_conflict
            )
        }
    
    def _check_expert_conflict(self, expert_decisions: dict) -> bool:
        """Check if experts significantly disagree"""
        scores = [d['score'] for d in expert_decisions.values()]
        if len(scores) < 2:
            return False
        
        # Calculate variance
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        
        # High variance indicates conflict
        return variance > 0.1
    
    def _get_routing_reason(self, is_high_confidence: bool, 
                           is_ambiguous: bool, 
                           has_conflict: bool) -> str:
        """Generate human-readable routing reason"""
        if is_high_confidence and not has_conflict:
            return "High confidence, clear decision → Fast template"
        elif is_ambiguous:
            return "Ambiguous score → LLM for nuanced explanation"
        elif has_conflict:
            return "Expert disagreement → LLM for reconciliation"
        else:
            return "Standard case → Template explanation"


# Global instances
explanation_generator = ExplanationGenerator()
orchestrator = ExplanationOrchestrator(explanation_generator)


@app.on_event("startup")
async def startup_event():
    """Start listening for alerts when service starts"""
    asyncio.create_task(process_alerts())


async def process_alerts():
    """Continuously process alerts from Redis"""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('alerts')
    
    print("🎯 Explanation Service started - listening for alerts...")
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                alert_data = json.loads(message['data'])
                await generate_and_publish_explanation(alert_data)
                
            except Exception as e:
                logging.error(f"Error processing alert: {e}")


async def generate_and_publish_explanation(alert_data):
    """Generate explanation using orchestrator and publish to dashboard"""
    try:
        transaction_id = alert_data['transaction']['transaction_id']
        
        # **FIX 1: Use orchestrator to route explanation**
        explanation_result = await orchestrator.route_explanation(alert_data)
        
        # Add explanation and metadata to alert
        alert_data['explanation'] = explanation_result['explanation']
        alert_data['explanation_type'] = explanation_result['explanation_type']
        alert_data['routing_reason'] = explanation_result['routing_reason']
        
        # **FIX 2: Store explanation for analytics**
        await redis_client.setex(
            f"explanation:{transaction_id}",
            86400,  # 24 hour TTL
            json.dumps(explanation_result)
        )
        
        # Publish to dashboard
        await redis_client.publish(
            'alerts_with_explanations', 
            json.dumps(alert_data, default=str)
        )
        
        print(f"📝 Generated {explanation_result['explanation_type']} explanation "
              f"for {transaction_id}")
        
    except Exception as e:
        logging.error(f"Error generating explanation: {e}")
        
        # Fallback: send alert without explanation
        alert_data['explanation'] = "Explanation generation failed"
        alert_data['explanation_type'] = "error"
        await redis_client.publish(
            'alerts_with_explanations',
            json.dumps(alert_data, default=str)
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "explanation_service",
        "cache_size": len(explanation_generator.explanation_cache)
    }


@app.get("/stats")
async def get_stats():
    """Get explanation generation statistics"""
    return {
        "cache_size": len(explanation_generator.explanation_cache),
        "cache_keys": list(explanation_generator.explanation_cache.keys())[:10]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)