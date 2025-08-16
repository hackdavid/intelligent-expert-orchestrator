from typing import Optional
from agentic_workflow.manager.expert_runner import BaseExpert


class MarketAnalystExpert(BaseExpert):
    """Market analysis expert for entrepreneurs"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__(
            name="market_analyst",
            description="Expert in market research, competitive analysis, and market opportunity assessment",
            correlation_id=correlation_id
        )
    
    def run(self, user_prompt: str) -> str:
        """Execute market analyst expert logic and return response"""
        try:
            # Provide market analysis
            analysis_prompt = f"""
            You are a market analysis expert. Provide market analysis for the following question:
            
            Question: {user_prompt}
            
            Provide analysis covering:
            1. Market size and opportunity
            2. Competitive landscape
            3. Target audience insights
            4. Market entry strategies
            """
            
            response = self.llm.quick_prompt(analysis_prompt, system="You are a market analysis expert. Provide insights on market research and analysis.")
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.logger.info(f"Market analyst response generated successfully")
            return response_text
            
        except Exception as e:
            self.logger.error(f"Market analyst execution failed: {str(e)}")
            raise e
