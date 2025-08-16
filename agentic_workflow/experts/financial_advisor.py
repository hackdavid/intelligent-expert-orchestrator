from typing import Optional
from agentic_workflow.manager.expert_runner import BaseExpert


class FinancialAdvisorExpert(BaseExpert):
    """Financial advisor expert for entrepreneurs"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__(
            name="financial_advisor",
            description="Expert in financial planning, funding strategies, and financial modeling for startups",
            correlation_id=correlation_id
        )
    
    def run(self, user_prompt: str) -> str:
        """Execute financial advisor expert logic and return response"""
        try:
            # Provide financial advice
            advice_prompt = f"""
            You are a financial advisor expert. Provide financial advice for the following question:
            
            Question: {user_prompt}
            
            Provide analysis covering:
            1. Financial planning considerations
            2. Funding options and strategies
            3. Financial modeling insights
            4. Risk assessment and mitigation
            """
            
            response = self.llm.quick_prompt(advice_prompt, system="You are a financial advisor expert. Provide financial guidance for entrepreneurs.")
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.logger.info(f"Financial advisor response generated successfully")
            return response_text
            
        except Exception as e:
            self.logger.error(f"Financial advisor execution failed: {str(e)}")
            raise e
