"""
Anna AI Coach Workflow using LangGraph
Main workflow orchestration for the Anna AI Coach system
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import traceback

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..resource import AnnaRequest, LoggerFactory, dev_draw_mermaid


@dataclass
class WorkflowState:
    """State object for the Anna workflow"""
    
    # Input request
    request: AnnaRequest
    
    # Processing flags
    needs_translation: bool = False
    source_language: str = "en"
    target_language: str = "en"
    
    # Context and history
    user_context: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Expert responses
    expert_responses: Dict[str, Any] = field(default_factory=dict)
    
    # Final response components
    summary: str = ""
    followup_questions: List[Dict[str, Any]] = field(default_factory=list)
    formatted_response: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    processing_steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_step(self, step_name: str):
        """Add a processing step to the workflow"""
        self.processing_steps.append(f"{step_name}: {datetime.now(timezone.utc).isoformat()}")
    
    def add_error(self, error: str):
        """Add an error to the workflow"""
        self.errors.append(f"{error}: {datetime.now(timezone.utc).isoformat()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "request": self.request.to_dict(),
            "needs_translation": self.needs_translation,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "user_context": self.user_context,
            "conversation_history": self.conversation_history,
            "expert_responses": self.expert_responses,
            "summary": self.summary,
            "followup_questions": self.followup_questions,
            "formatted_response": self.formatted_response,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_steps": self.processing_steps,
            "errors": self.errors
        }


class AnnaWorkflow:
    """Main workflow orchestrator for Anna AI Coach"""
    
    def __init__(self):
        """Initialize the Anna workflow"""
        self.memory = MemorySaver()
        self.context_store = {}  # Global dictionary for user context storage
        self.workflow = self._build_workflow()
        self.logger = LoggerFactory.get_logger("AnnaWorkflow")
        dev_draw_mermaid(self.workflow, prefix="anna_workflow_")
        self.logger.info("Anna workflow initialized successfully")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes to the graph
        workflow.add_node("pre_node", self._pre_node)
        workflow.add_node("pre_translation_node", self._pre_translation_node)
        workflow.add_node("context_management_node", self._context_management_node)
        workflow.add_node("expert_runner_node", self._expert_runner_node)
        workflow.add_node("summarizer_node", self._summarizer_node)
        workflow.add_node("followup_question_node", self._followup_question_node)
        workflow.add_node("response_formatter_node", self._response_formatter_node)
        workflow.add_node("context_update_node", self._context_update_node)
        workflow.add_node("post_translation_node", self._post_translation_node)
        workflow.add_node("post_node", self._post_node)        
        # Define the workflow edges
        workflow.set_entry_point("pre_node")
        
        # Main flow
        workflow.add_edge("pre_node", "pre_translation_node")
        workflow.add_edge("pre_translation_node", "context_management_node")
        workflow.add_edge("context_management_node", "expert_runner_node")
        workflow.add_edge("expert_runner_node", "summarizer_node")
        workflow.add_edge("summarizer_node", "followup_question_node")
        workflow.add_edge("followup_question_node", "response_formatter_node")
        workflow.add_edge("response_formatter_node", "context_update_node")
        workflow.add_edge("context_update_node", "post_translation_node")
        workflow.add_edge("post_translation_node", "post_node")
        workflow.add_edge("post_node", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    # Node implementations (placeholder methods - will be implemented in nodes.py)
    async def _pre_node(self, state: WorkflowState) -> WorkflowState:
        """Pre-processing node"""
        from .nodes import PreNode
        return await PreNode().run(state)
    
    async def _pre_translation_node(self, state: WorkflowState) -> WorkflowState:
        """Pre-translation node"""
        from .nodes import PreTranslationNode
        return await PreTranslationNode().run(state)
    
    async def _context_management_node(self, state: WorkflowState) -> WorkflowState:
        """Context management node"""
        from .nodes import ContextManagementNode
        correlation_id = state.request.user_context.correlation_id
        return await ContextManagementNode(self.context_store, correlation_id=correlation_id).run(state)
    
    
    async def _expert_runner_node(self, state: WorkflowState) -> WorkflowState:
        """Expert runner node using graph-based execution"""
        from agentic_workflow.manager.expert_runner import ExpertRunner
        
        try:
            # Create expert runner
            correlation_id = state.request.user_context.correlation_id
            expert_runner = ExpertRunner(request=state.request,correlation_id=correlation_id)

            # Run experts using graph-based approach
            expert_states = await expert_runner.run_experts(
                user_prompt=state.request.user_context.prompt,
                user_context=state.user_context
            )
            
            # Convert expert responses to a format compatible with workflow state
            expert_responses = {}
            for expert_name, expert_response in expert_states.items():
                expert_responses[expert_name] = {
                    "expert_name": expert_name,
                    "expert_response": expert_response.get('response',''),
                    "opt_in": 'True',
                    "error": expert_response.get('error', ''),
                    "execution_time": expert_response.get('execution_time', 0),
                }
            
            # Store expert responses in workflow state
            state.expert_responses = expert_responses
            
            # Add processing step
            state.add_step("expert_execution_completed")
            
            return state
            
        except Exception as e:
            state.add_error(f"Expert execution failed: {str(e)}")
            return state
    
    async def _summarizer_node(self, state: WorkflowState) -> WorkflowState:
        """Summarizer node"""
        from .nodes import SummarizerNode
        return await SummarizerNode().run(state)
    
    async def _followup_question_node(self, state: WorkflowState) -> WorkflowState:
        """Follow-up question node"""
        from .nodes import FollowupQuestionNode
        return await FollowupQuestionNode().run(state)
    
    async def _response_formatter_node(self, state: WorkflowState) -> WorkflowState:
        """Response formatter node"""
        from .nodes import ResponseFormatterNode
        return await ResponseFormatterNode().run(state)
    
    async def _context_update_node(self, state: WorkflowState) -> WorkflowState:
        """Context update node"""
        from .nodes import ContextUpdateNode
        correlation_id = state.request.user_context.correlation_id
        return await ContextUpdateNode(self.context_store, correlation_id=correlation_id).run(state)
    
    async def _post_translation_node(self, state: WorkflowState) -> WorkflowState:
        """Post-translation node"""
        from .nodes import PostTranslationNode
        return await PostTranslationNode().run(state)
    
    async def _post_node(self, state: WorkflowState) -> WorkflowState:
        """Post-processing node"""
        from .nodes import PostNode
        return await PostNode().run(state)
    
    
    async def process_request(self, request: AnnaRequest) -> Dict[str, Any]:
        """
        Process a request through the Anna workflow
        
        Args:
            request: AnnaRequest object containing user input
            
        Returns:
            Dictionary containing the final response and metadata
        """
        workflow_logger = LoggerFactory.get_workflow_logger(
            workflow_id=str(uuid.uuid4()),
            correlation_id=request.user_context.correlation_id
        )
        
        try:
            workflow_logger.log_workflow_step("workflow", "started", {
                "user_id": request.user_context.user_id,
                "session_id": request.user_context.session_id,
                "prompt": request.user_context.prompt[:100] + "..." if len(request.user_context.prompt) > 100 else request.user_context.prompt
            })
            
            # Create initial state
            initial_state = WorkflowState(request=request)
            
            # Run the workflow with checkpoint configuration
            config = {"configurable": {"thread_id": request.user_context.session_id}}
            
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            # Handle different return types
            if hasattr(final_state, 'end_time'):
                # It's a WorkflowState object
                final_state.end_time = datetime.now(timezone.utc)
                final_state.add_step("workflow_completed")
                workflow_logger.log_workflow_step("workflow", "completed", {
                    "workflow_id": final_state.workflow_id,
                    "status": "success",
                    "summary_preview": final_state.summary[:100] + "..." if final_state.summary else "N/A"
                })
                return final_state.formatted_response
            elif isinstance(final_state, dict):
                # It's a dictionary response
                workflow_logger.log_workflow_step("workflow", "completed", {
                    "workflow_id": initial_state.workflow_id,
                    "status": "success",
                    "response_type": "dict"
                })
                return final_state
            else:
                # Unknown return type
                workflow_logger.log_workflow_step("workflow", "completed", {
                    "workflow_id": initial_state.workflow_id,
                    "status": "success",
                    "response_type": str(type(final_state))
                })
                return {"response": str(final_state), "type": str(type(final_state))}
            
        except Exception as e:
            # Create error state
            error_state = WorkflowState(request=request)
            error_state.add_error(f"Workflow failed: {str(e)}")
            error_state.end_time = datetime.now(timezone.utc)
            
            workflow_logger.error(f"Workflow failed: {str(e)}", {
                "workflow_id": initial_state.workflow_id if 'initial_state' in locals() else "N/A",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            })
            raise
    
    def get_user_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get user context from global storage"""
        key = f"{user_id}_{session_id}"
        return self.context_store.get(key, {})
    
    def update_user_context(self, user_id: str, session_id: str, context: Dict[str, Any]):
        """Update user context in global storage"""
        key = f"{user_id}_{session_id}"
        self.context_store[key] = context


def main():
    """Test the Anna workflow"""
    print("=== Testing Anna Workflow ===")
    
    # Create a sample request
    from ..resource import AnnaRequest, UserContext, LanguageCode, RequestScope
    
    user_context = UserContext(
        user_id="test_user_123",
        session_id="test_session_456",
        prompt="How do I validate my business idea?",
        correlation_id="test_corr_789"
    )
    
    request = AnnaRequest(
        language=LanguageCode.ENGLISH,
        user_context=user_context,
        scope=RequestScope.BUSINESS_ADVICE
    )
    
    # Create and run workflow
    workflow = AnnaWorkflow()
    result = workflow.process_request(request)
    
    print(f"Workflow Result: {result}")
    print("=== Test completed! ===")


if __name__ == "__main__":
    main()
