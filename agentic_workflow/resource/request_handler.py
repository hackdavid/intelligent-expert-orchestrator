"""
Simple Request Handler for Anna AI Coach System
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timezone
import uuid


class LanguageCode(Enum):
    """Supported language codes"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    JAPANESE = "ja"
    HINDI = "hi"
    ARABIC = "ar"


@dataclass
class UserContext:
    """User context information"""
    prompt: str
    session_id: str
    user_id: str
    correlation_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    user_profile: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_profile is None:
            self.user_profile = {}


@dataclass
class FollowUpQuestion:
    """Follow-up question structure"""
    question: str
    question_id: Optional[str] = None
    context: Optional[str] = None
    options: Optional[List[str]] = None
    required: bool = False
    question_type: str = "text"
    
    def __post_init__(self):
        if not self.question_id:
            self.question_id = str(uuid.uuid4())


@dataclass
class UserSelection:
    """User selection for disambiguation"""
    selection_id: str
    selected_option: str
    context: Optional[str] = None
    confidence: float = 1.0
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class RequestMetadata:
    """Additional request metadata"""
    request_id: str
    timestamp: datetime
    source: str = "web"
    version: str = "1.0"
    priority: str = "normal"
    tags: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class AnnaRequest:
    """Main request structure for Anna AI Coach"""
    language: Dict[str, str]  # {"name": "English", "code": "en"}
    user_context: UserContext
    follow_up: Optional[List[FollowUpQuestion]] = None
    user_selection: Optional[UserSelection] = None
    scope: Optional[Dict[str, Any]] = None
    metadata: Optional[RequestMetadata] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.follow_up is None:
            self.follow_up = []
        if self.metadata is None:
            self.metadata = RequestMetadata(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc)
            )
        if self.additional_data is None:
            self.additional_data = {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnnaRequest':
        """Create AnnaRequest from dictionary"""
        # Convert datetime strings back to datetime objects
        def convert_datetime(obj):
            if isinstance(obj, str):
                try:
                    return datetime.fromisoformat(obj.replace('Z', '+00:00'))
                except ValueError:
                    return obj
            return obj
        
        def process_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    process_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            process_dict(item)
                else:
                    d[key] = convert_datetime(value)
        
        # Create a copy to avoid modifying original data
        processed_data = data.copy()
        process_dict(processed_data)
        
        # Reconstruct nested objects
        if 'user_context' in processed_data:
            processed_data['user_context'] = UserContext(**processed_data['user_context'])
        
        if 'follow_up' in processed_data and processed_data['follow_up']:
            processed_data['follow_up'] = [
                FollowUpQuestion(**q) for q in processed_data['follow_up']
            ]
        
        if 'user_selection' in processed_data and processed_data['user_selection']:
            processed_data['user_selection'] = UserSelection(**processed_data['user_selection'])
        
        if 'metadata' in processed_data and processed_data['metadata']:
            processed_data['metadata'] = RequestMetadata(**processed_data['metadata'])
        
        if 'scope' in processed_data and processed_data['scope']:
            try:
                processed_data['scope'] = RequestScope(processed_data['scope'])
            except ValueError:
                processed_data['scope'] = RequestScope.GENERAL
        
        return cls(**processed_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AnnaRequest to dictionary"""
        result = asdict(self)
        
        # Convert datetime objects to strings and enums to values
        def process_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    process_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            process_dict(item)
                elif isinstance(value, datetime):
                    d[key] = value.isoformat()
                elif isinstance(value, Enum):
                    d[key] = value.value
        
        process_dict(result)
        return result
    
    @classmethod
    def from_object(cls, obj: 'AnnaRequest') -> 'AnnaRequest':
        """Create AnnaRequest from another AnnaRequest object (copy)"""
        return cls.from_dict(obj.to_dict())


def main():
    """Test the request handler"""
    print("=== Testing AnnaRequest ===")
    
    # Sample request payload from frontend
    sample_payload = {
        "language": {"name": "English", "code": "en"},
        "user_context": {
            "prompt": "How do I validate my business idea?",
            "session_id": "session_123",
            "user_id": "user_456"
        },
        "scope": "validation",
        "follow_up": [
            {
                "question": "What industry is your business in?",
                "question_type": "multiple_choice",
                "options": ["Technology", "Healthcare", "Education"],
                "required": True
            }
        ],
        "user_selection": {
            "selection_id": "sel_001",
            "selected_option": "Technology",
            "confidence": 0.95
        },
        "additional_data": {"source": "web"}
    }
    
    print("1. Creating request from dictionary:")
    request = AnnaRequest.from_dict(sample_payload)
    print(f"   Request ID: {request.metadata.request_id}")
    print(f"   Language: {request.language}")
    print(f"   Scope: {request.scope.value}")
    print(f"   Prompt: {request.user_context.prompt}")
    print(f"   Follow-up questions: {len(request.follow_up)}")
    print(f"   User selection: {request.user_selection.selected_option if request.user_selection else 'None'}")
    print()
    
    print("2. Converting back to dictionary:")
    result_dict = request.to_dict()
    print(f"   Dictionary keys: {list(result_dict.keys())}")
    print(f"   Language: {result_dict['language']}")
    print(f"   Scope: {result_dict['scope']}")
    print()
    
    print("3. Creating copy from object:")
    copy_request = AnnaRequest.from_object(request)
    print(f"   Copy Request ID: {copy_request.metadata.request_id}")
    print(f"   Same prompt: {copy_request.user_context.prompt}")
    print(f"   Same scope: {copy_request.scope.value}")
    print()
    
    print("4. Testing with minimal payload:")
    minimal_payload = {
        "language": {"name": "Spanish", "code": "es"},
        "user_context": {
            "prompt": "¿Cómo valido mi idea?",
            "session_id": "session_es",
            "user_id": "user_es"
        }
    }
    
    minimal_request = AnnaRequest.from_dict(minimal_payload)
    print(f"   Language: {minimal_request.language}")
    print(f"   Prompt: {minimal_request.user_context.prompt}")
    print(f"   Scope: {minimal_request.scope.value if minimal_request.scope else 'None'}")
    print()
    
    print("=== Test completed successfully! ===")


if __name__ == "__main__":
    main()
