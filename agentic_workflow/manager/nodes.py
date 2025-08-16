"""
Anna AI Coach Workflow Nodes
Individual node implementations for the LangGraph workflow
"""

from typing import Dict, Any, List
import json
import logging
from datetime import datetime, timezone
import traceback
from abc import ABC, abstractmethod

from ..resource import AnnaLLMRegistry, LoggerFactory
from .workflow import WorkflowState


class BaseNode(ABC):
    """Base class for all workflow nodes"""
    
    def __init__(self, correlation_id: str = None):
        self.llm = AnnaLLMRegistry().get_coaching_llm()
        self.correlation_id = correlation_id
        self.logger = LoggerFactory.get_node_logger(
            self.__class__.__name__, 
            correlation_id=correlation_id
        )
    
    async def run(self, state: WorkflowState) -> WorkflowState:
        """Run the node logic"""
        # Update logger with state information if not already set
        if not self.correlation_id and hasattr(state, 'request'):
            self.correlation_id = state.request.user_context.correlation_id
            self.logger = LoggerFactory.get_node_logger(
                self.__class__.__name__, 
                correlation_id=self.correlation_id
            )
        
        try:
            self.logger.log_workflow_step(self.__class__.__name__, "started")
            result = await self._process(state)
            self.logger.log_workflow_step(self.__class__.__name__, "completed")
            return result
        except Exception as e:
            self.logger.error(f"Error in {self.__class__.__name__}: {e}", {
                "state_snapshot": state.to_dict(),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            })
            raise

    @abstractmethod
    async def _process(self, state: WorkflowState) -> WorkflowState:
        raise NotImplementedError


class PreNode(BaseNode):
    """Pre-processing node - logs request and prepares for processing"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Pre-process the request"""
        # Log the incoming request
        self.logger.info(f"Processing request: {state.request.user_context.user_id}")
        
        # Add request metadata to state
        state.user_context["request_timestamp"] = datetime.now(timezone.utc).isoformat()
        state.user_context["request_id"] = state.workflow_id
        
        # Check if request needs special handling
        if state.request.user_context.prompt.lower().startswith("urgent"):
            state.user_context["priority"] = "high"
        
        return state


class PreTranslationNode(BaseNode):
    """Pre-translation node - detects language and translates if needed"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Handle pre-translation logic"""
        user_prompt = state.request.user_context.prompt
        target_lang = state.request.language
        
        # Simple language detection (in production, use a proper language detection service)
        if self._detect_language(user_prompt) != target_lang:
            state.needs_translation = True
            state.source_language = self._detect_language(user_prompt)
            state.target_language = target_lang
            
            # Translate the user prompt
            translated_prompt = self._translate_text(user_prompt, state.source_language, state.target_language)
            state.request.user_context.prompt = translated_prompt
            
            self.logger.info(f"Translated from {state.source_language} to {state.target_language}")
        
        return state
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection (placeholder)"""
        # In production, use a proper language detection service
        # For now, assume English
        return "en"
    
    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text (placeholder)"""
        # In production, use a proper translation service
        # For now, return the original text
        return text


class ContextManagementNode(BaseNode):
    """Context management node - retrieves and enriches user context"""
    
    def __init__(self, context_store: Dict[str, Any], correlation_id: str = None):
        super().__init__(correlation_id=correlation_id)
        self.context_store = context_store
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Manage user context"""
        user_id = state.request.user_context.user_id
        session_id = state.request.user_context.session_id
        
        # Get existing context
        context_key = f"{user_id}_{session_id}"
        existing_context = self.context_store.get(context_key, {})
        
        # Enrich context with current request
        enriched_context = {
            "user_id": user_id,
            "session_id": session_id,
            "last_interaction": datetime.now(timezone.utc).isoformat(),
            "interaction_count": existing_context.get("interaction_count", 0) + 1,
            "preferences": existing_context.get("preferences", {}),
            "business_context": existing_context.get("business_context", {}),
            "conversation_history": existing_context.get("conversation_history", [])
        }
        
        # Add current interaction to history
        enriched_context["conversation_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": state.request.user_context.prompt,
            "scope": state.request.scope
        })
        
        # Update state
        state.user_context = enriched_context
        
        return state

    
    def ExpertRunnerNode(self, expert: str, state: WorkflowState) -> Dict[str, Any]:
        """Fallback method to run a specific expert (legacy implementation)"""
        import time
        start_time = time.time()
        
        prompt = state.request.user_context.prompt
        context = state.user_context
        
        # Expert-specific system prompts
        expert_system_prompts = {
            "business_strategist": """You are a business strategy expert. Provide actionable business advice for entrepreneurs.

Provide a structured response with:
1. Key insights
2. Actionable steps
3. Potential challenges
4. Success metrics""",
            
            "motivation_coach": """You are a motivational coach for entrepreneurs. Provide encouragement and motivation.

Provide a response that:
1. Acknowledges their situation
2. Offers encouragement
3. Shares relevant success stories
4. Provides actionable motivation""",
            
            "market_analyst": """You are a market analysis expert. Provide insights on market research and analysis.

Provide analysis covering:
1. Market size and opportunity
2. Competitive landscape
3. Target audience insights
4. Market entry strategies""",
            
            "general_advisor": """You are Anna, an AI coach for entrepreneurs. Provide helpful and actionable advice.

Provide comprehensive advice that is:
1. Practical and actionable
2. Based on entrepreneurial best practices
3. Encouraging and supportive
4. Tailored to their specific situation"""
        }
        
        system_prompt = expert_system_prompts.get(expert, expert_system_prompts["general_advisor"])
        
        try:
            response = self.llm.quick_prompt(prompt, system=system_prompt)
            
            # Handle different response formats
            if hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', str(response))
            else:
                response_text = str(response)
            
            duration = time.time() - start_time
            
            # Log expert response
            self.logger.log_expert_response(
                expert_name=expert,
                response=response_text,
                duration=duration,
                extra_data={
                    "prompt": prompt,
                    "system_prompt": system_prompt
                }
            )
            
            return {
                "expert": expert,
                "response": response_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed"
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Expert {expert} failed: {str(e)}", {
                "expert": expert,
                "prompt": prompt,
                "duration": duration,
                "error": str(e)
            })
            raise


class SummarizerNode(BaseNode):
    """Summarizer node - consolidates expert responses"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Summarize expert responses"""
        if not state.expert_responses:
            state.summary = "I'm unable to provide advice at the moment."
            return state
        
        # Create summary prompt
        expert_responses_text = "\n\n".join([
            f"Expert {expert}: {response.get('expert_response', 'No response')}"
            for expert, response in state.expert_responses.items()
        ])
        
        summary_prompt = f"""
        You are Anna, an AI coach for entrepreneurs. Summarize and synthesize the following expert responses into a cohesive, actionable response.
        
        Original Question: {state.request.user_context.prompt}
        
        Expert Responses:
        {expert_responses_text}
        
        Provide a comprehensive summary that:
        1. Addresses the user's question directly
        2. Combines the best insights from all experts
        3. Provides clear, actionable steps
        4. Maintains a supportive and encouraging tone
        5. Is well-structured and easy to follow
        """
        
        response = self.llm.quick_prompt(summary_prompt)
        
        # Handle different response formats
        if hasattr(response, 'content'):
            state.summary = response.content
        elif isinstance(response, dict):
            state.summary = response.get('content', str(response))
        else:
            state.summary = str(response)
        
        return state


class FollowupQuestionNode(BaseNode):
    """Follow-up question node - generates relevant follow-up questions"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Generate follow-up questions"""
        if not state.summary:
            state.followup_questions = []
            return state
        
        followup_prompt = f"""
        Based on the user's question and the response provided, generate 3 relevant follow-up questions that would help the user further.
        
        Original Question: {state.request.user_context.prompt}
        Response: {state.summary}
        
        Generate follow-up questions that:
        1. Are specific and actionable
        2. Help the user dive deeper into the topic
        3. Address potential next steps
        4. Are relevant to their business context
        
        Return as JSON array with objects containing 'question' and 'category' fields.
        """
        
        try:
            response = self.llm.quick_prompt(followup_prompt, json_output=True)
            if hasattr(response, 'content'):
                followup_questions = json.loads(response.content)
            else:
                followup_questions = response
            state.followup_questions = followup_questions
        except Exception as e:
            # Fallback questions
            state.followup_questions = [
                {"question": "Would you like me to elaborate on any specific aspect?", "category": "clarification"},
                {"question": "What's your next immediate step?", "category": "action_planning"},
                {"question": "Do you have any concerns about implementing this advice?", "category": "concerns"}
            ]
            self.logger.warning(f"Follow-up question generation failed: {e}")
        
        return state


class ResponseFormatterNode(BaseNode):
    """Response formatter node - formats final response"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Format the final response"""
        formatted_response = {
            "workflow_id": state.workflow_id,
            "status": "success",
            "response": {
                "summary": state.summary,
                "followup_questions": state.followup_questions,
                "expert_insights": state.expert_responses,
            },
            "metadata": {
                "processing_time": (datetime.now(timezone.utc) - state.start_time).total_seconds(),
                "language": state.target_language,
                "needs_translation": state.needs_translation,
                "processing_steps": state.processing_steps
            }
        }
        
        state.formatted_response = formatted_response
        return state


class ContextUpdateNode(BaseNode):
    """Context update node - updates user context with new information"""
    
    def __init__(self, context_store: Dict[str, Any], correlation_id: str = None):
        super().__init__(correlation_id=correlation_id)
        self.context_store = context_store
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Update user context"""
        user_id = state.request.user_context.user_id
        session_id = state.request.user_context.session_id
        context_key = f"{user_id}_{session_id}"
        
        # Update context with new information
        updated_context = state.user_context.copy()
        updated_context.update({
            "last_response": state.summary,
            "response_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_interactions": updated_context.get("interaction_count", 0)
        })
        
        # Store updated context
        self.context_store[context_key] = updated_context
        
        return state


class PostTranslationNode(BaseNode):
    """Post-translation node - translates response back to user's language"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Handle post-translation"""
        if not state.needs_translation:
            return state
        
        # Translate summary
        if state.summary:
            translated_summary = self._translate_text(
                state.summary, 
                state.target_language, 
                state.source_language
            )
            state.summary = translated_summary
        
        # Translate follow-up questions
        if state.followup_questions:
            for question in state.followup_questions:
                if "question" in question:
                    question["question"] = self._translate_text(
                        question["question"],
                        state.target_language,
                        state.source_language
                    )
        
        return state
    
    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text (placeholder)"""
        # In production, use a proper translation service
        # For now, return the original text
        return text


class PostNode(BaseNode):
    """Post-processing node - final processing and logging"""
    
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """Post-process the response"""
        # Log successful completion
        self.logger.info(f"Workflow completed successfully: {state.workflow_id}")
        
        # Add completion metadata
        state.user_context["completion_timestamp"] = datetime.now(timezone.utc).isoformat()
        state.user_context["processing_duration"] = (
            datetime.now(timezone.utc) - state.start_time
        ).total_seconds()
        
        # Update formatted response with final metadata
        if state.formatted_response:
            state.formatted_response["metadata"]["completion_time"] = datetime.now(timezone.utc).isoformat()
        
        return state


# Export all node classes
__all__ = [
    'BaseNode',
    'PreNode',
    'PreTranslationNode',
    'ContextManagementNode',
    'SummarizerNode',
    'FollowupQuestionNode',
    'ResponseFormatterNode',
    'ContextUpdateNode',
    'PostTranslationNode',
    'PostNode',
]
