"""
Manager module for Anna AI Coach System
Contains the main workflow orchestration using LangGraph
"""

from .workflow import AnnaWorkflow, WorkflowState
from .nodes import (
    PreNode,
    PreTranslationNode,
    ContextManagementNode,
    SummarizerNode,
    FollowupQuestionNode,
    ResponseFormatterNode,
    ContextUpdateNode,
    PostTranslationNode,
    PostNode
)

__all__ = [
    'AnnaWorkflow',
    'WorkflowState',
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

__version__ = "1.0.0"
