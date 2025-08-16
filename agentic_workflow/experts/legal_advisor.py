from typing import Optional
from agentic_workflow.manager.expert_runner import BaseExpert


class LegalAdvisorExpert(BaseExpert):
    """Legal advisor expert for entrepreneurs"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__(
            name="legal_advisor",
            description="Expert in legal matters, compliance, and business law for startups",
            correlation_id=correlation_id
        )
    
    def run(self, user_prompt: str) -> str:
        """Execute legal advisor expert logic and return response"""
        try:
            # Provide legal guidance
            advice_prompt = f"""
            You are a legal advisor expert. Provide legal guidance for the following question:
            
            Question: {user_prompt}
            
            Provide analysis covering:
            1. Legal considerations and requirements
            2. Compliance and regulatory issues
            3. Risk assessment and mitigation
            4. Recommended legal steps
            """
            
            response = self.llm.quick_prompt(advice_prompt, system="You are a legal advisor expert. Provide legal guidance for entrepreneurs.")
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.logger.info(f"Legal advisor response generated successfully")
            return response_text
            
        except Exception as e:
            self.logger.error(f"Legal advisor execution failed: {str(e)}")
            raise e
