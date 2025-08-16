"""
Anna LLM Service for Anna AI Coach System using Azure OpenAI
"""

import os
from enum import Enum
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models import AzureChatOpenAI
from dotenv import load_dotenv
from .logger import LoggerFactory


class BaseAnnaLLM:
    """Base class for Anna LLM implementations"""

    def __init__(self, model_ref):
        """Initialize base Anna LLM"""
        print(f"Creating AnnaLLM for model {model_ref}")
        self.model_ref = model_ref


class AnnaAzureLLM(BaseAnnaLLM):
    """Azure OpenAI implementation for Anna LLM"""
    MIN_API_VERSION = "2024-08-01-preview"

    def __init__(self, model_ref: str):
        """Initialize Azure OpenAI LLM for Anna"""
        super().__init__(model_ref)

        # Load environment variables
        load_dotenv()

        # Basic configuration
        self.temperature = None
        self.set_temperature(0.25)
        self.max_retries = 2
        self.request_timeout = 120
        
        # Initialize logger
        self.logger = LoggerFactory.get_llm_logger()

        # Azure OpenAI configuration - possibly independent of model name
        self.azure_openai_api_key = os.environ.get('AZURE_OPENAI_API_KEY_' + model_ref,
                                                   os.environ.get('AZURE_OPENAI_API_KEY'))
        self.azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT_' + model_ref,
                                                    os.environ.get('AZURE_OPENAI_ENDPOINT'))
        
        if not self.azure_openai_api_key or not self.azure_openai_endpoint:
            raise ValueError("Missing environment variable for Azure OpenAI.")

        # Model-specific configuration
        try:
            self.model_name = os.environ['MODEL_NAME_' + model_ref]
            self.deployment_name = os.environ['DEPLOYMENT_NAME_' + model_ref]
            self.openai_api_version = os.environ['OPENAI_API_VERSION_' + model_ref]
            self.openai_api_type = os.environ['OPENAI_API_TYPE_' + model_ref]
        except KeyError:
            print(f"Missing environment variable for Azure OpenAI model {model_ref}.")
            raise

    def set_temperature(self, temperature):
        """Set the temperature and provide guidance warnings for different ranges.
           Lower values (0.0 - 0.3): Deterministic and consistent responses.
           Medium values (0.4 - 0.7): Balance between creativity and reliability.
           Higher values (0.8 - 2.0): Random and creative, but less predictable.
           Temperature values outside the range [0, 2] are adjusted to the nearest limit.
        """
        temperature = max(0, min(temperature, 2))
        if temperature >= 0.3:
            print(f'LLM temperature is at or above "creative": {temperature}')

        self.temperature = temperature

    def _get_llm(self, streaming: bool, **kwargs):
        """Get LangChain LLM instance with configuration"""
        model_params = dict(
            streaming=streaming, 
            temperature=self.temperature, 
            max_retries=self.max_retries,
            request_timeout=self.request_timeout, 
            openai_api_type=self.openai_api_type,
            azure_endpoint=self.azure_openai_endpoint, 
            openai_api_key=self.azure_openai_api_key,
            deployment_name=self.deployment_name, 
            openai_api_version=self.openai_api_version
        )
        
        if kwargs:
            model_params.update(kwargs)

        if model_params['openai_api_version'] < self.MIN_API_VERSION:
            model_params['openai_api_version'] = self.MIN_API_VERSION

        return AzureChatOpenAI(**model_params)

    @property
    def llm_buffering(self):
        """Get non-streaming LLM instance"""
        return self._get_llm(streaming=False)

    @property
    def llm_streaming(self):
        """Get streaming LLM instance"""
        return self._get_llm(streaming=True)
    
    def quick_prompt(self, human: str, system: str = None, json_output: bool = False, **kwargs):
        """
        Quick synchronous prompt for Anna LLM
        
        Args:
            human: User message
            system: System message (optional)
            json_output: Whether to return JSON output
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response
        """
        import time
        start_time = time.time()
        
        if system:
            msgs = [("system", system), ("user", human)]
        else:
            msgs = [("user", human)]
            
        chat_template = ChatPromptTemplate.from_messages(msgs)
        chat = chat_template.format_messages()
        
        try:
            if json_output:
                response = self.llm_buffering.with_structured_output(method="json_mode").invoke(chat, **kwargs)
            else:
                response = self.llm_buffering.invoke(chat, **kwargs)
            
            duration = time.time() - start_time
            
            # Log the LLM call
            response_content = response.content if hasattr(response, 'content') else str(response)
            self.logger.log_llm_call(
                prompt=human,
                response=response_content,
                model=self.model_name,
                duration=duration,
                extra_data={
                    "system_prompt": system,
                    "json_output": json_output,
                    "model_ref": self.model_ref
                }
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"LLM call failed: {str(e)}", {
                "prompt": human,
                "system_prompt": system,
                "model": self.model_name,
                "duration": duration,
                "error": str(e)
            })
            raise
    
    async def quick_prompt_async(self, human: str, system: str = None, json_output: bool = False, **kwargs):
        """
        Quick asynchronous prompt for Anna LLM
        
        Args:
            human: User message
            system: System message (optional)
            json_output: Whether to return JSON output
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response
        """
        if system:
            msgs = [("system", system), ("user", human)]
        else:
            msgs = [("user", human)]
            
        chat_template = ChatPromptTemplate.from_messages(msgs)
        chat = chat_template.format_messages()
        
        if json_output:
            response = await self.llm_buffering.with_structured_output(method="json_mode").ainvoke(chat, **kwargs)
        else:
            response = await self.llm_buffering.ainvoke(chat, **kwargs)

        return response
    
    def quick_prompt_with_messages(self, messages: list, json_output: bool = False, **kwargs):
        """
        Quick prompt with custom messages list
        
        Args:
            messages: List of message tuples [(role, content), ...]
            json_output: Whether to return JSON output
            **kwargs: Additional parameters for LLM call
            
        Returns:
            LLM response
        """
        chat_template = ChatPromptTemplate.from_messages(messages)
        chat = chat_template.format_messages()
        
        if json_output:
            response = self.llm_buffering.with_structured_output(method="json_mode").invoke(chat, **kwargs)
        else:
            response = self.llm_buffering.invoke(chat, **kwargs)

        return response


class AnnaLLMRegistry:
    """Registry for Anna LLM models"""

    class Models(str, Enum):
        """List all the Models supported by Anna LLM"""
        ANNA_GPT4O = "ANNA_GPT4O"

    DEFAULT_MODEL = Models.ANNA_GPT4O

    @property
    def supported_models(self):
        """Get list of supported model names"""
        return [x.value for x in self.Models]

    def get_llm(self, model_name: Models = None):
        """Get LLM instance by model name"""
        if not model_name:
            print(f"No model name provided. Using default: {self.DEFAULT_MODEL}")
            model_name = self.DEFAULT_MODEL

        if model_name not in self.Models:
            raise ValueError(f"LLM model name {model_name} is not configured in the registry.")
        else:
            return AnnaAzureLLM(model_name)  # All models are Azure for now

    def get_llm_by_name(self, model_name: str):
        """Get LLM instance by string name"""
        return self.get_llm(self.Models(model_name.upper()))

    def get_coaching_llm(self):
        """Get the default coaching LLM"""
        return self.get_llm(self.Models.ANNA_GPT4O)

    def get_reasoning_llm(self):
        """Get the reasoning LLM for complex analysis"""
        return self.get_llm(self.Models.ANNA_GPT4_1)





def test_anna_registry():
    """Test the Anna LLM registry"""
    for mdl in AnnaLLMRegistry.Models:
        print(f"=========== Checking {mdl.value} ===========")
        try:
            llm = AnnaLLMRegistry().get_llm(mdl)
            c = llm.llm_buffering.invoke("Are you ready to coach entrepreneurs?").content
            print(f"Anna LLM {mdl} says: {c}")
        except Exception as e:
            print(f"Failed to create {mdl}: {e}")


def main():
    """Test the Anna LLM service"""
    print("=== Testing Anna LLM Service ===")
    
    try:
        # Test registry
        # print("1. Testing Anna LLM Registry:")
        # # test_anna_registry()
        # print()
        
        # Test specific model
        print("2. Testing specific model:")
        llm = AnnaLLMRegistry().get_coaching_llm()
        print(f"   Using model: {llm.model_ref}")
        print(f"   Temperature: {llm.temperature}")
        print()
        
        # Test quick prompt
        print("3. Testing quick prompt:")
        system_prompt = "You are Anna, an AI coach for entrepreneurs. Be helpful and provide actionable advice."
        user_prompt = "How do I validate my business idea?"
        print(f"prompt: {user_prompt}")
        response = llm.quick_prompt(user_prompt, system_prompt)
        print(f"   Response: {response.content}")
        print()
        
        # Test JSON output
        print("4. Testing JSON output:")
        json_system_prompt = "You are an AI assistant that provides structured responses about business validation."
        json_user_prompt = "Provide 3 steps to validate a business idea in JSON format with 'steps' as an array."
        
        json_response = llm.quick_prompt(json_user_prompt, json_system_prompt, json_output=True)
        print(f"   JSON Response: {json_response}")
        print()
        
        # Test custom messages
        print("5. Testing custom messages:")
        messages = [
            ("system", "You are a business advisor."),
            ("user", "What is the most important thing for a startup?"),
            ("assistant", "Focus on customer validation."),
            ("user", "How do I do that?")
        ]
        
        custom_response = llm.quick_prompt_with_messages(messages)
        print(f"   Custom Response: {custom_response.content[:200]}...")
        print()
        
        print("=== Test completed successfully! ===")
        
    except Exception as e:
        print(f"Test failed: {e}")
        print("Make sure to set up your environment variables properly.")


if __name__ == "__main__":
    main()
