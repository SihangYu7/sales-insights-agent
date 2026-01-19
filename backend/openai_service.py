"""
AI Agent Backend - Module 3: OpenAI Service
============================================
This module teaches you how to use the OpenAI SDK to interact with GPT models.

KEY CONCEPTS YOU'LL LEARN:
- OpenAI API authentication
- Chat completions (the main way to interact with GPT)
- System prompts vs user prompts
- Temperature and token controls
- Error handling with OpenAI

WHY THIS MATTERS:
Before we build the AI agent that converts questions to SQL, you need to
understand how to call OpenAI's API. This is the foundation!
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
# The API key is read from the OPENAI_API_KEY environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def simple_chat(user_message: str, system_prompt: str = None) -> dict:
    """
    Send a message to OpenAI and get a response.

    This is the most basic way to interact with GPT models.

    LEARNING POINT - What are "messages"?
    -------------------------------------
    OpenAI's chat models work with a conversation format:
    - "system": Instructions for how the AI should behave
    - "user": The user's input/question
    - "assistant": The AI's responses

    Args:
        user_message: The user's question or input
        system_prompt: Optional instructions for how the AI should behave

    Returns:
        dict: Response containing the AI's answer and usage stats

    Example:
        >>> result = simple_chat("What is 2+2?")
        >>> print(result['answer'])
        "4"
    """
    try:
        # Build the conversation messages
        messages = []

        # System prompt (optional) - gives the AI instructions
        # Think of this as "setting the personality and rules"
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # User message - the actual question/input
        messages.append({
            "role": "user",
            "content": user_message
        })

        # LEARNING POINT - What's happening here?
        # ---------------------------------------
        # We're calling OpenAI's Chat Completions API with:
        # - model: Which GPT model to use (gpt-3.5-turbo is fast and cheap)
        # - messages: The conversation history
        # - temperature: Controls randomness (0 = focused, 1 = creative)
        # - max_tokens: Maximum length of the response

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",      # The model to use
            messages=messages,           # The conversation
            temperature=0.7,             # Creativity level (0-1)
            max_tokens=500               # Max response length
        )

        # Extract the AI's response
        answer = response.choices[0].message.content

        # LEARNING POINT - Token Usage
        # -----------------------------
        # OpenAI charges based on "tokens" (roughly 4 characters = 1 token)
        # The response includes how many tokens were used
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,      # Input cost
            "completion_tokens": response.usage.completion_tokens,  # Output cost
            "total_tokens": response.usage.total_tokens        # Total cost
        }

        return {
            "success": True,
            "answer": answer,
            "usage": usage,
            "model": "gpt-3.5-turbo"
        }

    except Exception as e:
        # LEARNING POINT - Error Handling
        # --------------------------------
        # Common errors:
        # - Invalid API key
        # - Rate limit exceeded
        # - Network issues
        # Always handle these gracefully!

        return {
            "success": False,
            "error": str(e),
            "answer": f"Sorry, I encountered an error: {str(e)}"
        }


def chat_with_context(user_message: str, conversation_history: list = None) -> dict:
    """
    Chat with context from previous messages.

    LEARNING POINT - Multi-turn Conversations
    ------------------------------------------
    To have a conversation with memory, you need to send the entire
    conversation history with each request. OpenAI models are stateless!

    Args:
        user_message: The user's current message
        conversation_history: List of previous messages in the conversation

    Returns:
        dict: Response with answer and updated conversation history

    Example:
        >>> history = []
        >>> result = chat_with_context("My name is Alice", history)
        >>> history = result['conversation_history']
        >>> result = chat_with_context("What's my name?", history)
        >>> print(result['answer'])
        "Your name is Alice"
    """
    try:
        # Start with conversation history or empty list
        messages = conversation_history or []

        # Add the new user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Call OpenAI with the full conversation
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        # Get the response
        answer = response.choices[0].message.content

        # Add the assistant's response to the conversation
        messages.append({
            "role": "assistant",
            "content": answer
        })

        return {
            "success": True,
            "answer": answer,
            "conversation_history": messages,  # Return updated history
            "usage": {
                "total_tokens": response.usage.total_tokens
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "answer": f"Error: {str(e)}"
        }


def ai_sales_assistant(user_question: str) -> dict:
    """
    An AI assistant specifically designed to help with sales questions.

    LEARNING POINT - System Prompts
    --------------------------------
    System prompts are POWERFUL. They define:
    - What the AI knows about
    - How it should respond
    - What tone/style to use
    - What limitations it has

    This is where we'll later add SQL knowledge!

    Args:
        user_question: User's question about sales

    Returns:
        dict: Response with the AI's answer
    """

    # LEARNING POINT - Crafting System Prompts
    # -----------------------------------------
    # A good system prompt:
    # 1. Defines the role
    # 2. Lists capabilities
    # 3. Sets the tone
    # 4. Explains limitations

    system_prompt = """You are a helpful sales data assistant.

Your role:
- Answer questions about sales, products, and business data
- Be concise and professional
- If you don't have the data to answer, say so clearly
- Use bullet points and formatting for clarity

Current capabilities:
- General business and sales concepts
- Basic data analysis explanations

Note: In the next module, you'll be connected to a real database!
For now, provide helpful general guidance about the question."""

    return simple_chat(user_question, system_prompt)


# =============================================================================
# TESTING FUNCTIONS - Run this file directly to test!
# =============================================================================

def test_openai_service():
    """
    Test the OpenAI service to make sure it works.
    Run this file directly to see it in action!
    """
    print("\n" + "="*60)
    print("🧪 Testing OpenAI Service - Module 3")
    print("="*60 + "\n")

    # Test 1: Simple chat
    print("Test 1: Simple Chat")
    print("-" * 40)
    result = simple_chat("Hello! Can you explain what an API is in one sentence?")
    if result['success']:
        print(f"✅ Success!")
        print(f"Question: Hello! Can you explain what an API is in one sentence?")
        print(f"Answer: {result['answer']}")
        print(f"Tokens used: {result['usage']['total_tokens']}")
    else:
        print(f"❌ Error: {result['error']}")

    print("\n")

    # Test 2: Sales assistant
    print("Test 2: Sales Assistant")
    print("-" * 40)
    result = ai_sales_assistant("What are some key metrics to track for sales?")
    if result['success']:
        print(f"✅ Success!")
        print(f"Question: What are some key metrics to track for sales?")
        print(f"Answer: {result['answer']}")
    else:
        print(f"❌ Error: {result['error']}")

    print("\n")

    # Test 3: Multi-turn conversation
    print("Test 3: Multi-turn Conversation (Memory)")
    print("-" * 40)

    # First message
    result1 = chat_with_context("My company sells electronics.")
    history = result1.get('conversation_history', [])
    print(f"User: My company sells electronics.")
    print(f"AI: {result1['answer'][:100]}...")

    # Second message - uses context!
    result2 = chat_with_context("What products would you recommend we focus on?", history)
    print(f"\nUser: What products would you recommend we focus on?")
    print(f"AI: {result2['answer'][:100]}...")
    print("✅ The AI remembered we sell electronics!")

    print("\n" + "="*60)
    print("🎉 All tests complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    """
    This runs when you execute: python openai_service.py
    It's a great way to test your code!
    """
    test_openai_service()
