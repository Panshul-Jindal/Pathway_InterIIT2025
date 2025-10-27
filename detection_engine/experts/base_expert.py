# detection_engine/experts/base_expert.py
from abc import ABC, abstractmethod
from shared.schemas import Transaction, ExpertDecision
from typing import List, Dict, Any

class BaseExpert(ABC):
    def __init__(self, name: str, model_type: str):
        self.name = name
        self.model_type = model_type
    
    @abstractmethod
    def predict(self, transaction: Transaction) -> ExpertDecision:
        pass
    
    def calculate_confidence(self, transaction: Transaction) -> float:
        """Default confidence calculation"""
        return 0.8  # Override in subclasses

