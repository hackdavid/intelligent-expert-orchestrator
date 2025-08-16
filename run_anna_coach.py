#!/usr/bin/env python3
"""
Anna AI Coach - Interactive Runner Script
Simple script to run the Anna AI Coach system interactively
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any
import traceback
# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agentic_workflow.manager.workflow import AnnaWorkflow
from agentic_workflow.resource import AnnaRequest, UserContext, LanguageCode


def create_default_request() -> Dict[str, Any]:
    """
    Create a default AnnaRequest dictionary structure
    
    Returns:
        Dictionary with default AnnaRequest structure
    """
    return {
        "language": {
            "name": "English",
            "code": "en"
        },
        "user_context": {
            "user_id": "interactive_user",
            "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "prompt": "",
            "correlation_id": f"corr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        },
        "follow_up": None,
        "user_selection": None,
        "scope": "",
        "metadata": {
            "source": "interactive_script",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        "additional_data": {}
    }


def get_user_prompt() -> str:
    """
    Get user prompt from command line input
    
    Returns:
        User's question/prompt
    """
    print("\n" + "="*60)
    print("🤖 Anna AI Coach - Interactive Mode")
    print("="*60)
    print("Ask me anything about business, strategy, finance, legal, or technical topics!")
    print("Type 'quit' or 'exit' to stop the session.")
    print("-"*60)
    
    while True:
        try:
            prompt = input("\n💬 Your question: ").strip()
            
            if not prompt:
                print("❌ Please enter a question.")
                continue
                
            if prompt.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye! Thanks for using Anna AI Coach.")
                sys.exit(0)
                
            return prompt
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thanks for using Anna AI Coach.")
            sys.exit(0)
        except EOFError:
            print("\n\n👋 Goodbye! Thanks for using Anna AI Coach.")
            sys.exit(0)


def update_request_with_prompt(request_dict: Dict[str, Any], prompt: str) -> AnnaRequest:
    """
    Update the request dictionary with user prompt and create AnnaRequest object
    
    Args:
        request_dict: Base request dictionary
        prompt: User's question/prompt
        
    Returns:
        AnnaRequest object
    """
    # Update the prompt in user_context
    request_dict["user_context"]["prompt"] = prompt
    
    # Update correlation_id with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    request_dict["user_context"]["correlation_id"] = f"corr_{timestamp}"
    request_dict["user_context"]["session_id"] = f"session_{timestamp}"
    
    # Update metadata timestamp
    request_dict["metadata"]["timestamp"] = datetime.now().isoformat()
    
    # Create AnnaRequest object
    user_context = UserContext(
        user_id=request_dict["user_context"]["user_id"],
        session_id=request_dict["user_context"]["session_id"],
        prompt=request_dict["user_context"]["prompt"],
        correlation_id=request_dict["user_context"]["correlation_id"]
    )
    
    return AnnaRequest(
        language=LanguageCode.ENGLISH.value,
        user_context=user_context,
        scope={}
    )


def print_response(response: Dict[str, Any]):
    """
    Print the workflow response in a formatted way
    
    Args:
        response: Response from the workflow
    """
    print("\n" + "="*60)
    print("🤖 Anna AI Coach Response")
    print("="*60)
    
    if not response:
        print("❌ No response received from the workflow.")
        return
    
    formated_response = response.get('formatted_response',{})
    if formated_response:
        print("📄 Response:")
        print(formated_response.get('response', {}).get('summary', 'No summary available'))
    else:
        print("📄 Response:")
        print(response.get('content', 'No content available'))


async def run_anna_coach():
    """
    Main function to run Anna AI Coach interactively
    """
    print("🚀 Starting Anna AI Coach...")
    
    try:
        # Initialize the workflow
        print("📋 Initializing workflow...")
        workflow = AnnaWorkflow()
        print("✅ Workflow initialized successfully!")
        
        # Create default request structure
        request_dict = create_default_request()
        
        print(f"📝 Default request structure created:")
        print(f"   • Language: {request_dict['language']['name']}")
        print(f"   • Scope: {request_dict['scope']}")
        print(f"   • User ID: {request_dict['user_context']['user_id']}")
        
        # Main interaction loop
        while True:
            # Get user prompt
            prompt = get_user_prompt()
            
            # Update request with user prompt
            print(f"🔄 Processing your question...")
            request = update_request_with_prompt(request_dict, prompt)
            
            try:
                # Run the workflow

                print(f"⚙️  Running workflow with correlation ID: {request.user_context.correlation_id}")
                response = await workflow.process_request(request)

                # Print the response
                print_response(response)

            except Exception as e:
                print(f"\n❌ Error processing request: {str(e)}")
                print("Please try again with a different question.")
                print("Error details:",traceback.format_exc())
            
            # Ask if user wants to continue
            print("\n" + "-"*60)
            continue_choice = input("🔄 Ask another question? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', '']:
                print("👋 Goodbye! Thanks for using Anna AI Coach.")
                break
    
    except Exception as e:
        print(f"❌ Failed to initialize Anna AI Coach: {str(e)}")
        print("Please check your configuration and try again.")
        return


def main():
    """
    Main entry point
    """
    print("🎯 Anna AI Coach - Interactive Runner")
    print("This script allows you to interact with the Anna AI Coach system.")
    
    # Check if environment is set up
    if not os.path.exists(".env"):
        print("⚠️  Warning: No .env file found. Make sure to set up your environment variables.")
        print("   You can copy env_sample.txt to .env and fill in your credentials.")
    
    # Run the interactive session
    try:
        asyncio.run(run_anna_coach())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using Anna AI Coach.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
