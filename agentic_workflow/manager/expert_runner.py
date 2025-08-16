import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Type,Annotated
from datetime import datetime, timezone
from langgraph.graph import add_messages
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agentic_workflow.resource import AnnaLLMRegistry, LoggerFactory, ExpertDecision, dev_draw_mermaid


class ExpertStatus(Enum):
    """Expert execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    OPTED_OUT = "opted_out"


@dataclass
class ExpertResponse:
    """Individual expert response"""
    name: str
    request: str = ""
    response: str = ""
    opt_in: str = ""
    error: str = ""
    execution_time: float = 0.0
    status: ExpertStatus = ExpertStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

def merge_expert_responses(existing: Dict[str, ExpertResponse], new: Dict[str, ExpertResponse]) -> Dict[str, ExpertResponse]:
    """Merge function: updates existing dict with new entries"""
    merged = dict(existing)
    merged.update(new)   # new responses overwrite by key
    return merged

def merge_metadata(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge function: combine metadata dicts, new values overwrite old ones"""
    merged = dict(existing)
    merged.update(new)
    return merged

def latest_timestamp(old: str, new: str) -> str:
    """Always keep the latest timestamp value"""
    return new

@dataclass
class ExpertRunnerState:
    """State for expert runner containing multiple expert responses"""
    expert_responses: Annotated[Dict[str, ExpertResponse], merge_expert_responses] = field(default_factory=dict)
    metadata: Annotated[
        Dict[str, Any],
        merge_metadata
    ] = field(default_factory=dict)
    timestamp: Annotated[str, latest_timestamp] = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseExpert(ABC):
    """Base class for all experts"""
    
    def __init__(self, name: str, description: str, correlation_id: Optional[str] = None):
        self.name = name
        self.description = description
        self.correlation_id = correlation_id
        self.llm = AnnaLLMRegistry().get_coaching_llm()
        self.logger = LoggerFactory.get_expert_logger(name, correlation_id)
    
    def opt_in(self, user_prompt: str) -> bool:
        """
        Determine if this expert should opt-in to answer the user's question
        
        Args:
            user_prompt: The user's request/prompt
            
        Returns:
            True if the expert should answer, False otherwise
        """
        try:
            # Create expert decision instance
            expert_decision = ExpertDecision(
                expert_name=self.name,
                description=self.description,
                correlation_id=self.correlation_id
            )
            
            # Make decision on whether to opt-in
            should_answer = expert_decision.make_decision(user_prompt)
            
            self.logger.info(f"Expert {self.name} opt-in decision: {should_answer}")
            return should_answer
            
        except Exception as e:
            self.logger.error(f"Failed to make opt-in decision for {self.name}: {str(e)}")
            # Default to False (don't answer) if there's an error
            return False
    
    @abstractmethod
    def run(self, user_prompt: str) -> str:
        """Execute the expert's main logic and return response"""
        pass


class ExpertRegistry:
    """Registry for managing experts"""
    
    def __init__(self):
        self._experts: Dict[str, Type[BaseExpert]] = {}
        self.logger = LoggerFactory.get_logger("ExpertRegistry")
    
    def register_expert(self, expert_class: Type[BaseExpert]) -> None:
        """Register an expert class"""
        expert_name = expert_class.__name__
        self._experts[expert_name] = expert_class
        self.logger.info(f"Registered expert: {expert_name}")
    
    def get_expert_class(self, expert_name: str) -> Optional[Type[BaseExpert]]:
        """Get expert class by name"""
        return self._experts.get(expert_name)
    
    def get_all_expert_names(self) -> List[str]:
        """Get all registered expert names"""
        return list(self._experts.keys())


class ExpertRunner:
    """Main expert runner that manages expert execution using LangGraph"""
    
    def __init__(self,request= None, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id
        self.registry = ExpertRegistry()
        self.logger = LoggerFactory.get_logger("ExpertRunner", correlation_id)
        self.memory = MemorySaver()
        self._setup_default_experts()
        self.request = request
        self.graph = self._build_expert_graph()
        dev_draw_mermaid(self.graph, prefix="expert_runner_")
        self.logger.info("Expert runner initialized with graph-based execution")

    def _setup_default_experts(self):
        """Setup default experts"""
        from agentic_workflow.experts.business_strategist import BusinessStrategistExpert
        from agentic_workflow.experts.market_analyst import MarketAnalystExpert
        from agentic_workflow.experts.financial_advisor import FinancialAdvisorExpert
        from agentic_workflow.experts.legal_advisor import LegalAdvisorExpert
        from agentic_workflow.experts.technical_advisor import TechnicalAdvisorExpert
        
        self.registry.register_expert(BusinessStrategistExpert)
        self.registry.register_expert(MarketAnalystExpert)
        self.registry.register_expert(FinancialAdvisorExpert)
        self.registry.register_expert(LegalAdvisorExpert)
        self.registry.register_expert(TechnicalAdvisorExpert)
    
    def register_custom_expert(self, expert_class: Type[BaseExpert]) -> None:
        """Register a custom expert"""
        self.registry.register_expert(expert_class)
        self.logger.info(f"Registered custom expert: {expert_class.__name__}")
    
    def _build_expert_graph(self) -> StateGraph:
        """Build the expert execution graph with parallel expert nodes"""
        
        # Create the state graph
        graph = StateGraph(ExpertRunnerState)
        
        # Add pre-processing node
        graph.add_node("pre_node", self._pre_node)
        
        # Add expert nodes dynamically
        expert_names = self.registry.get_all_expert_names()
        for expert_name in expert_names:
            graph.add_node(f"expert_{expert_name}", self._create_expert_node(expert_name))
        
        # Add post-processing node
        graph.add_node("post_node", self._post_node)
        
        # Define the workflow edges
        graph.set_entry_point("pre_node")
        
        # Connect pre_node to all expert nodes (parallel execution)
        for expert_name in expert_names:
            graph.add_edge("pre_node", f"expert_{expert_name}")
        
        # Connect all expert nodes to post_node (collect results)
        for expert_name in expert_names:
            graph.add_edge(f"expert_{expert_name}", "post_node")
        
        # Connect post_node to END
        graph.add_edge("post_node", END)
        
        return graph.compile(checkpointer=self.memory)
    
    def _pre_node(self, state: ExpertRunnerState) -> ExpertRunnerState:
        """Pre-processing node for expert execution"""
        self.logger.info(f"Starting expert execution for request...")
        state.metadata["pre_processing_completed"] = True
        state.metadata["expert_count"] = len(self.registry.get_all_expert_names())
        return state
    
    def _create_expert_node(self, expert_name: str):
        """Create a node function for a specific expert"""
        def expert_node(state: ExpertRunnerState) -> ExpertRunnerState:
            return self._execute_expert(expert_name, state)
        return expert_node
    
    def _execute_expert(self, expert_name: str, state: ExpertRunnerState) -> ExpertRunnerState:
        """Execute a specific expert and update the state"""
        try:
            # Create expert instance
            expert_class = self.registry.get_expert_class(expert_name)
            if not expert_class:
                self.logger.error(f"Expert class not found: {expert_name}")
                expert_response = ExpertResponse(
                    name=expert_name,
                    opt_in="no",
                    error=f"Expert class not found: {expert_name}",
                    status=ExpertStatus.FAILED
                )
                state.expert_responses[expert_name] = expert_response
                return state
            
            expert = expert_class(correlation_id=self.correlation_id)
            
            # Check if expert should opt-in
            should_answer = expert.opt_in(self.request.user_context.prompt)
            
            if not should_answer:
                expert_response = ExpertResponse(
                    name=expert_name,
                    opt_in="no",
                    status=ExpertStatus.OPTED_OUT
                )
                state.expert_responses[expert_name] = expert_response
                self.logger.info(f"Expert {expert_name} opted out")
                return state
            
            # Execute expert if opted in
            start_time = datetime.now(timezone.utc)
            response = expert.run(self.request.user_context.prompt)
            end_time = datetime.now(timezone.utc)
            
            # Update execution time
            execution_time = (end_time - start_time).total_seconds()
            
            # Create expert response
            expert_response = ExpertResponse(
                name=expert_name,
                response=response,
                opt_in="yes",
                execution_time=execution_time,
                status=ExpertStatus.COMPLETED,
                metadata={"completed_at": end_time.isoformat()}
            )
            
            state.expert_responses[expert_name] = expert_response
            
            self.logger.info(f"Expert {expert_name} completed in {execution_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Expert {expert_name} failed: {str(e)}")
            expert_response = ExpertResponse(
                name=expert_name,
                opt_in="no",
                error=str(e),
                status=ExpertStatus.FAILED
            )
            state.expert_responses[expert_name] = expert_response
        
        return state
    
    def _post_node(self, state: ExpertRunnerState) -> ExpertRunnerState:
        """Post-processing node to collect and summarize expert responses"""
        self.logger.info(f"Expert execution completed for {len(state.expert_responses)} experts")
        
        # Update metadata
        state.metadata["post_processing_completed"] = True
        state.metadata["completed_experts"] = len(state.expert_responses)
        state.timestamp = datetime.now(timezone.utc).isoformat()
        
        return state
    
    async def run_experts(self, user_prompt: str, user_context: Dict[str, Any], 
                         expert_names: Optional[List[str]] = None) -> Dict[str, ExpertResponse]:
        """Run experts using the graph-based approach"""
        self.logger.info(f"Starting graph-based expert execution")

        # Use all experts if none specified
        if expert_names is None:
            expert_names = self.registry.get_all_expert_names()
        
        # Create initial state
        initial_state = ExpertRunnerState()
        
        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            final_reponse = {}
            for expert,response in final_state.get('expert_responses',{}).items():
                if response.opt_in in ['yes','Yes','YES','true','True',True]:
                    final_reponse[expert] = {
                        'name': expert,
                        'response': response.response,
                        'error': response.error,
                        'execution_time': response.execution_time,
                        'status': response.status.value,
                    }
            return final_reponse
            
        except Exception as e:
            self.logger.error(f"Failed to run experts: {str(e)}")
            # Return error responses for all experts
            error_responses = {}
            for expert_name in expert_names:
                error_responses[expert_name] = ExpertResponse(
                    name=expert_name,
                    error=str(e),
                    status=ExpertStatus.FAILED
                )
            return error_responses
    
    def get_available_experts(self) -> List[str]:
        """Get list of available experts"""
        return self.registry.get_all_expert_names()
    
    def get_expert_info(self, expert_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific expert"""
        expert_class = self.registry.get_expert_class(expert_name)
        if not expert_class:
            return None
        
        # Create temporary instance to get description
        temp_instance = expert_class()
        return {
            "name": expert_name,
            "description": temp_instance.description,
            "class": expert_class.__name__
        }


if __name__ == "__main__":
    # Test the expert runner
    async def test_expert_runner():
        print("=== Testing New Graph-Based Expert Runner ===")
        
        # Create expert runner
        runner = ExpertRunner("test-correlation-123")
        
        # Test user prompt
        user_prompt = "How do I validate my business idea for a SaaS product?"
        user_context = {"user_id": "test_user", "session_id": "test_session"}
        
        print(f"User Prompt: {user_prompt}")
        print(f"Available Experts: {runner.get_available_experts()}")
        
        # Test graph-based execution
        print("\n--- Testing Graph-Based Execution ---")
        results = await runner.run_experts(user_prompt, user_context)
        
        print(f"\nResults ({len(results)} experts):")
        for expert_name, expert_response in results.items():
            print(f"\n{expert_name}:")
            print(f"  Status: {expert_response.status.value}")
            print(f"  Opt-in: {expert_response.opt_in}")
            print(f"  Execution Time: {expert_response.execution_time:.2f}s")
            if expert_response.error:
                print(f"  Error: {expert_response.error}")
            if expert_response.response:
                print(f"  Response Preview: {expert_response.response[:200]}...")
    
    # Run the test
    asyncio.run(test_expert_runner())
