# shared/schemas.py
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class Transaction(BaseModel):
    transaction_id: str
    timestamp: datetime
    amount: float
    customer_id: str
    merchant_id: str
    location: str
    device_id: str
    transaction_type: str
    features: Dict[str, float]

class ExpertDecision(BaseModel):
    expert_name: str
    score: float
    confidence: float
    contributing_factors: List[Dict[str, Any]]
    model_type: str

class EnsembleDecision(BaseModel):
    transaction_id: str
    final_score: float
    expert_decisions: Dict[str, ExpertDecision]
    weights: Dict[str, float]
    primary_factors: List[Dict[str, Any]]
    needs_human_review: bool

class Alert(BaseModel):
    alert_id: str
    transaction: Transaction
    ensemble_decision: EnsembleDecision
    explanation: Optional[str]
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime

class Feedback(BaseModel):
    alert_id: str
    correct_label: bool  # True if fraud, False if legitimate
    analyst_notes: Optional[str]
    feedback_timestamp: datetime