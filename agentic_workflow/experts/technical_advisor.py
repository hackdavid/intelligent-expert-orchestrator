from typing import Optional
from agentic_workflow.manager.expert_runner import BaseExpert


class TechnicalAdvisorExpert(BaseExpert):
    """Technical advisor expert for entrepreneurs"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__(
            name="technical_advisor",
            description="Expert in technology, product development, and technical architecture for startups",
            correlation_id=correlation_id
        )
    
    def run(self, user_prompt: str) -> str:
        """Execute technical advisor expert logic and return response"""
        try:
            # Provide technical guidance
            advice_prompt = f"""
            You are a technical advisor expert. Provide technical guidance for the following question:
            
            Question: {user_prompt}
            
            Provide analysis covering:
            1. Technical architecture considerations
            2. Technology stack recommendations
            3. Development approach and methodology
            4. Technical risk assessment
            """
            
            response = self.llm.quick_prompt(advice_prompt, system="You are a technical advisor expert. Provide technical guidance for entrepreneurs.")
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.logger.info(f"Technical advisor response generated successfully")
            return response_text
            
        except Exception as e:
            self.logger.error(f"Technical advisor execution failed: {str(e)}")
            raise e
