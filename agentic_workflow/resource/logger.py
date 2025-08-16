"""
Custom Logger for Anna AI Coach System
Provides structured logging with correlation_id and user_id tracking
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class AnnaLogger:
    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.name = name
        self.correlation_id = correlation_id
        self.project_root = self._get_project_root()
        self.log_dir = self.project_root / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"anna.{name}")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _get_project_root(self) -> Path:
        current = Path.cwd()
        while current != current.parent:
            if (current / ".env").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _setup_handlers(self):
        # Create formatter
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handlers
        self._setup_file_handlers(formatter)

    def _setup_file_handlers(self, formatter):
        # General log file
        general_handler = logging.FileHandler(self.log_dir / "anna_general.log", encoding='utf-8')
        general_handler.setLevel(logging.DEBUG)
        general_handler.setFormatter(formatter)
        self.logger.addHandler(general_handler)
        
        # Correlation-specific log file
        if self.correlation_id:
            correlation_handler = logging.FileHandler(self.log_dir / f"correlation_{self.correlation_id}.log", encoding='utf-8')
            correlation_handler.setLevel(logging.DEBUG)
            correlation_handler.setFormatter(formatter)
            self.logger.addHandler(correlation_handler)

    def _format_message(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": self.name,
            "message": message
        }
        if self.correlation_id:
            log_data["correlation_id"] = self.correlation_id
        if extra_data:
            log_data["extra"] = extra_data
        return json.dumps(log_data, ensure_ascii=False, default=str)

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.logger.debug(self._format_message(message, extra_data))

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.logger.info(self._format_message(message, extra_data))

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.logger.warning(self._format_message(message, extra_data))

    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.logger.error(self._format_message(message, extra_data))

    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.logger.critical(self._format_message(message, extra_data))

    # Specialized logging methods
    def log_workflow_step(self, step: str, status: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log workflow step with status"""
        step_data = {"step": step, "status": status}
        if extra_data:
            step_data.update(extra_data)
        self.info(f"Workflow step: {step} - {status}", step_data)

    def log_llm_call(self, prompt: str, response: str, model: str, duration: float, extra_data: Optional[Dict[str, Any]] = None):
        """Log LLM call with performance metrics"""
        llm_data = {
            "prompt": prompt,
            "response": response,
            "model": model,
            "duration": duration
        }
        if extra_data:
            llm_data.update(extra_data)
        self.info(f"LLM call completed in {duration:.2f}s", llm_data)

    def log_expert_response(self, expert_name: str, response: str, duration: float, extra_data: Optional[Dict[str, Any]] = None):
        """Log expert response with performance metrics"""
        expert_data = {
            "expert": expert_name,
            "response": response,
            "duration": duration
        }
        if extra_data:
            expert_data.update(extra_data)
        self.info(f"Expert {expert_name} responded in {duration:.2f}s", expert_data)

    def log_user_interaction(self, user_id: str, session_id: str, action: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log user interaction"""
        interaction_data = {
            "user_id": user_id,
            "session_id": session_id,
            "action": action
        }
        if extra_data:
            interaction_data.update(extra_data)
        self.info(f"User interaction: {action}", interaction_data)


class LoggerFactory:
    @staticmethod
    def get_logger(name: str, correlation_id: Optional[str] = None) -> AnnaLogger:
        return AnnaLogger(name, correlation_id)
    
    @staticmethod
    def get_workflow_logger(workflow_id: str, correlation_id: Optional[str] = None) -> AnnaLogger:
        return AnnaLogger(f"workflow.{workflow_id}", correlation_id)
    
    @staticmethod
    def get_node_logger(node_name: str, correlation_id: Optional[str] = None) -> AnnaLogger:
        return AnnaLogger(f"node.{node_name}", correlation_id)
    
    @staticmethod
    def get_llm_logger(correlation_id: Optional[str] = None) -> AnnaLogger:
        return AnnaLogger("llm", correlation_id)
    
    @staticmethod
    def get_expert_logger(expert_name: str, correlation_id: Optional[str] = None) -> AnnaLogger:
        return AnnaLogger(f"expert.{expert_name}", correlation_id)


# Utility functions for log analysis
def find_logs_by_correlation_id(correlation_id: str) -> list:
    """Find all logs for a specific correlation ID"""
    try:
        # Find project root
        current = Path.cwd()
        while current != current.parent:
            if (current / ".env").exists():
                log_dir = current / "logs"
                break
            current = current.parent
        else:
            log_dir = Path.cwd() / "logs"
        
        correlation_file = log_dir / f"correlation_{correlation_id}.log"
        if not correlation_file.exists():
            return []
        
        logs = []
        with open(correlation_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Extract JSON part after the timestamp prefix
                    if '|' in line:
                        json_part = line.split('|', 3)[-1].strip()
                    else:
                        json_part = line
                    
                    try:
                        log_entry = json.loads(json_part)
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        return logs
    except Exception as e:
        print(f"Error reading logs for correlation_id {correlation_id}: {e}")
        return []


def search_logs(query: str, log_file: str = "anna_general.log") -> list:
    """Search logs for specific terms"""
    try:
        # Find project root
        current = Path.cwd()
        while current != current.parent:
            if (current / ".env").exists():
                log_dir = current / "logs"
                break
            current = current.parent
        else:
            log_dir = Path.cwd() / "logs"
        
        log_file_path = log_dir / log_file
        if not log_file_path.exists():
            return []
        
        matching_logs = []
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if query.lower() in line.lower():
                    # Extract JSON part after the timestamp prefix
                    if '|' in line:
                        json_part = line.split('|', 3)[-1].strip()
                    else:
                        json_part = line
                    
                    try:
                        log_entry = json.loads(json_part)
                        matching_logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        return matching_logs
    except Exception as e:
        print(f"Error searching logs: {e}")
        return []


if __name__ == "__main__":
    # Test the logger
    logger = LoggerFactory.get_logger("test", "test-correlation-123")
    
    logger.info("Test message", {"key": "value"})
    logger.log_workflow_step("test_step", "started", {"user_id": "user123"})
    logger.log_llm_call("test prompt", "test response", "gpt-4", 1.5)
    logger.log_expert_response("business_strategist", "expert advice", 2.0)
    
    # Test log search
    logs = find_logs_by_correlation_id("test-correlation-123")
    print(f"Found {len(logs)} logs for test-correlation-123")
    
    search_results = search_logs("test")
    print(f"Found {len(search_results)} logs containing 'test'")
