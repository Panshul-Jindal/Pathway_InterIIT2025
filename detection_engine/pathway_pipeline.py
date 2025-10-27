# detection_engine/pathway_pipeline.py
import pathway as pw
from typing import Dict, Any
from shared.schemas import Transaction

def build_fraud_pipeline(experts, weight_manager):
    """Build the core Pathway streaming pipeline"""
    
    # Define input schema for transactions
    class TransactionSchema(pw.Schema):
        transaction_id: str
        amount: float
        customer_id: str
        merchant_id: str
        location: str
        device_id: str
        features: Dict[str, float]
    
    # Create input connector (simulated stream)
    transactions = pw.demo.range_stream(nb_rows=100000, schema=TransactionSchema)
    
    # Feature engineering with Pathway
    enriched_transactions = transactions.select(
        *pw.this.all(),
        # Velocity features (simplified)
        amount_velocity=pw.this.amount / 1000,
        location_risk=pw.apply(lambda loc: hash(loc) % 10, pw.this.location)
    )
    
    # Expert predictions (would integrate with actual expert classes)
    def expert_predictions_wrapper(transaction_data):
        # This would call the actual expert predict methods
        # Simplified for prototype
        return {
            'xgboost_score': 0.1,
            'rule_score': 0.2,
            'streaming_score': 0.15
        }
    
    predictions = enriched_transactions.select(
        *pw.this.all(),
        **expert_predictions_wrapper(pw.this)
    )
    
    # Ensemble combination
    final_scores = predictions.select(
        *pw.this.all(),
        ensemble_score=(
            pw.this.xgboost_score * 0.4 +
            pw.this.rule_score * 0.4 + 
            pw.this.streaming_score * 0.2
        )
    )
    
    # Output alerts
    alerts = final_scores.filter(pw.this.ensemble_score > 0.5)
    
    return alerts