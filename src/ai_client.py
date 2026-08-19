import os
from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt

class GeminiClient:
    """Client wrapper for persistent chat sessions using the genai SDK."""

    def __init__(self, system_instruction: str, api_key: str, model: str):
        """Initializes the GeminiClient instance.

        Args:
            system_instruction (str): System-level directives for the model.
            api_key (str): Authentication token for API access.
            model (str): Target model identifier.

        Raises:
            ValueError: If api_key is null or empty.
        """
        if not api_key:
            raise ValueError("API Key is missing. Please set it in settings.")
            
        # Initialize client payload
        self.client = genai.Client(api_key=api_key)
        
        # Define content generation configuration
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                )
            ]
        )
        
        # Instantiate active chat session
        self.chat = self.client.chats.create(
            model=model, 
            config=config
        )
    
    # Configure retry mechanism with exponential backoff and attempt limits
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def send_message(self, message: str) -> str:
        """Transmits a message payload to the chat session.

        Args:
            message (str): The input prompt string.

        Returns:
            str: The generated response string.
        """
        response = self.chat.send_message(message)
        return response.text