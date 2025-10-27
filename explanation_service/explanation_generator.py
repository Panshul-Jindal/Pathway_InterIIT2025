# explanation_service/explanation_generator.py
import google.generativeai as genai
import os
from typing import Dict, Any
import json
import asyncio

class ExplanationGenerator:
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
        self.explanation_cache = {}
        
    async def generate_explanation(self, alert_data: Dict[str, Any]) -> str:
        """Generate human-readable explanation for alert"""
        
        cache_key = self._generate_cache_key(alert_data)
        if cache_key in self.explanation_cache:
            return self.explanation_cache[cache_key]
        
        ensemble_decision = alert_data['ensemble_decision']
        final_score = ensemble_decision['final_score']
        
        # Use template for simple cases, LLM for complex ones
        if final_score > 0.8 or final_score < 0.2:
            explanation = self._generate_template_explanation(ensemble_decision)
        else:
            explanation = await self._generate_gemini_explanation(ensemble_decision)
        
        self.explanation_cache[cache_key] = explanation
        return explanation
    
    async def _generate_gemini_explanation(self, ensemble_decision: Dict) -> str:
        """Generate detailed explanation using Gemini"""
        try:
            prompt = self._build_gemini_prompt(ensemble_decision)
            
            # Gemini API call (synchronous, so we run in thread pool)
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            return response.text
            
        except Exception as e:
            print(f"Gemini explanation failed: {e}")
            return self._generate_template_explanation(ensemble_decision)
    
    def _build_gemini_prompt(self, ensemble_decision: Dict) -> str:
        """Build prompt for Gemini"""
        expert_breakdown = []
        for expert_name, decision in ensemble_decision['expert_decisions'].items():
            expert_breakdown.append(
                f"{expert_name}: score={decision['score']:.3f}, "
                f"confidence={decision['confidence']:.2f}"
            )
        
        prompt = f"""
You are a fraud analysis expert. Provide clear, concise explanations of fraud detection decisions.

**Transaction Risk Score**: {ensemble_decision['final_score']:.3f}

**Expert Analysis**:
{chr(10).join(expert_breakdown)}

**Primary Risk Factors**:
{chr(10).join([f"- {factor['description']}" for factor in ensemble_decision['primary_factors']])}

Please provide a clear summary explaining:
1. Why this transaction was flagged
2. The most influential risk factors  
3. Recommended actions
4. Confidence level in the assessment

Write in professional language for financial analysts.
"""
        return prompt
    
    # Keep the same template explanation and cache methods from before
    def _generate_template_explanation(self, ensemble_decision: Dict) -> str:
        # ... same implementation as before
        final_score = ensemble_decision['final_score']
        primary_factors = ensemble_decision['primary_factors']
        
        if final_score > 0.8:
            risk_level = "HIGH RISK"
            action = "Recommend: BLOCK transaction and require verification"
        elif final_score > 0.6:
            risk_level = "MEDIUM-HIGH RISK" 
            action = "Recommend: Require 2FA verification"
        elif final_score > 0.4:
            risk_level = "MEDIUM RISK"
            action = "Recommend: Flag for human review"
        else:
            risk_level = "LOW RISK"
            action = "Recommend: Allow with monitoring"
        
        factors_text = "\n".join([
            f"• {factor['description']} (impact: {factor['impact']:.2f})"
            for factor in primary_factors[:3]
        ])
        
        explanation = f"""
🔍 **FRAUD ALERT ANALYSIS**

**Risk Level**: {risk_level}
**Confidence Score**: {final_score:.3f}

**Primary Risk Factors**:
{factors_text}

**Expert Consensus**: {len(ensemble_decision['expert_decisions'])} experts analyzed this transaction

**Action**: {action}
"""
        return explanation.strip()
    
    def _generate_cache_key(self, alert_data: Dict) -> str:
        factors = alert_data['ensemble_decision']['primary_factors']
        factor_strings = [f["description"] for f in factors]
        return hash(tuple(factor_strings))
    






class ExplanationOrchestrator:
    def __init__(self, generator: ExplanationGenerator):
        self.generator = generator
        
    async def route_explanation(self, alert_data: Dict) -> str:
        """Orchestrator decides: template vs LLM"""
        ensemble_decision = alert_data['ensemble_decision']
        final_score = ensemble_decision['final_score']
        
        # Decision logic from your diagram
        is_high_confidence = final_score > 0.8 or final_score < 0.2
        is_ambiguous = 0.3 <= final_score <= 0.7
        
        if is_high_confidence:
            # Template path
            return self.generator._generate_template_explanation(ensemble_decision)
        elif is_ambiguous:
            # LLM path with SAR draft
            return await self.generator._generate_gemini_explanation(ensemble_decision)
        else:
            # Default to template
            return self.generator._generate_template_explanation(ensemble_decision)

