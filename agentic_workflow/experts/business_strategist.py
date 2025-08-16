from typing import Optional
from agentic_workflow.manager.expert_runner import BaseExpert


class BusinessStrategistExpert(BaseExpert):
    """Business strategy expert for entrepreneurs"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__(
            name="business_strategist",
            description="Expert in business strategy, market positioning, and competitive analysis for startups and entrepreneurs",
            correlation_id=correlation_id
        )
    
    def run(self, user_prompt: str) -> str:
        """Execute business strategy expert logic and return response"""
        try:
            # Provide business strategy advice
            advice_prompt = f"""
            You are a business strategy expert. Provide comprehensive business advice for the following question:
            
            Question: {user_prompt}
            
            Provide a structured response with:
            1. Key insights
            2. Actionable steps
            3. Potential challenges
            4. Success metrics
            """
            
            response = self.llm.quick_prompt(advice_prompt, system="You are a business strategy expert. Provide actionable business advice for entrepreneurs.")
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.logger.info(f"Business strategist response generated successfully")
            return response_text
            
        except Exception as e:
            self.logger.error(f"Business strategist execution failed: {str(e)}")
            raise e
    

