"""
Expert Decision Module
Handles expert opt-in decision logic for the Anna AI Coach system
"""

from typing import Optional
from .llm_service import AnnaLLMRegistry
from .logger import LoggerFactory


class ExpertDecision:
    """Handles expert opt-in decision logic"""
    
    def __init__(self, expert_name: str, description: str, correlation_id: Optional[str] = None):
        """
        Initialize the ExpertDecision class
        
        Args:
            expert_name: Name of the expert
            description: Description of the expert's expertise
            correlation_id: Optional correlation ID for logging
        """
        self.expert_name = expert_name
        self.description = description
        self.correlation_id = correlation_id
        self.llm = AnnaLLMRegistry().get_coaching_llm()
        self.logger = LoggerFactory.get_expert_logger(expert_name, correlation_id)
    
    def make_decision(self, user_prompt: str) -> bool:
        """
        Make a decision on whether the expert should answer the user's question
        
        Args:
            user_prompt: The user's question/prompt
            
        Returns:
            True if the expert should answer, False otherwise
        """
        try:
            # Create the decision prompt
            decision_prompt = f"""
            You are a {self.expert_name} expert. Based on the user's question, decide if you should provide advice.
            
            Expert Description: {self.description}
            User Question: {user_prompt}
            
            Respond with only 'yes' or 'no' based on whether this question requires {self.expert_name} expertise.
            """
            
            # Get the decision from LLM
            response = self.llm.quick_prompt(
                decision_prompt, 
                system=f"You are a {self.expert_name} expert. Respond with only 'yes' or 'no'."
            )
            
            # Extract the decision
            decision_text = response.content.strip().lower() if hasattr(response, 'content') else str(response).strip().lower()
            
            # Determine the decision
            should_answer = decision_text in ['yes', 'true', '1']
            
            self.logger.info(f"Expert decision for '{self.expert_name}': {decision_text} -> {should_answer}")
            
            return should_answer
            
        except Exception as e:
            self.logger.error(f"Failed to make decision for {self.expert_name}: {str(e)}")
            # Default to False (don't answer) if there's an error
            return False
    
    def get_decision_reasoning(self, user_prompt: str) -> tuple[bool, str]:
        """
        Make a decision and return both the decision and reasoning
        
        Args:
            user_prompt: The user's question/prompt
            
        Returns:
            Tuple of (decision: bool, reasoning: str)
        """
        try:
            # Create the decision prompt with reasoning request
            decision_prompt = f"""
            You are a {self.expert_name} expert. Based on the user's question, decide if you should provide advice.
            
            Expert Description: {self.description}
            User Question: {user_prompt}
            
            First, respond with only 'yes' or 'no' based on whether this question requires {self.expert_name} expertise.
            Then, provide a brief explanation of your reasoning.
            
            Format your response as:
            Decision: [yes/no]
            Reasoning: [your explanation]
            """
            
            # Get the decision from LLM
            response = self.llm.quick_prompt(
                decision_prompt, 
                system=f"You are a {self.expert_name} expert. Provide clear decision and reasoning."
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse the response
            lines = response_text.strip().split('\n')
            decision = False
            reasoning = "No reasoning provided"
            
            for line in lines:
                line = line.strip()
                if line.lower().startswith('decision:'):
                    decision_text = line.split(':', 1)[1].strip().lower()
                    decision = decision_text in ['yes', 'true', '1']
                elif line.lower().startswith('reasoning:'):
                    reasoning = line.split(':', 1)[1].strip()
            
            self.logger.info(f"Expert decision with reasoning for '{self.expert_name}': {decision} - {reasoning}")
            
            return decision, reasoning
            
        except Exception as e:
            self.logger.error(f"Failed to make decision with reasoning for {self.expert_name}: {str(e)}")
            return False, f"Error occurred: {str(e)}"


# Factory function for creating expert decisions
def create_expert_decision(expert_name: str, description: str, correlation_id: Optional[str] = None) -> ExpertDecision:
    """
    Factory function to create an ExpertDecision instance
    
    Args:
        expert_name: Name of the expert
        description: Description of the expert's expertise
        correlation_id: Optional correlation ID for logging
        
    Returns:
        ExpertDecision instance
    """
    return ExpertDecision(expert_name, description, correlation_id)
