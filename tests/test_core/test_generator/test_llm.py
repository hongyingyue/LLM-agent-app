import os
from dotenv import load_dotenv
from litellm import completion
from loguru import logger
import json

load_dotenv()


def test_chatgpt_api():
    """
    A simple test function to demonstrate using the ChatGPT API
    """
    try:
        # Make sure you have set your OpenAI API key in .env file
        # OPENAI_API_KEY=your_api_key_here
        
        # Example prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]
        
        # Call the API
        response = completion(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=100
        )
        
        # Log the response
        logger.info(f"Response: {response.choices[0].message.content}")
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error calling ChatGPT API: {str(e)}")
        raise


def test_function_calling():
    """
    A test function to demonstrate function calling capabilities with ChatGPT API
    """
    try:
        # Define the functions that the model can call
        functions = [
            {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit to use"
                        }
                    },
                    "required": ["location"]
                }
            }
        ]

        # Example conversation with function calling
        messages = [
            {"role": "system", "content": "You are a helpful assistant that can get weather information."},
            {"role": "user", "content": "What's the weather like in New York?"}
        ]

        # Call the API with function definitions
        response = completion(
            model="gpt-4.1-mini",
            messages=messages,
            functions=functions,
            function_call="auto",
            temperature=0.7
        )

        # Log the response
        logger.info(f"Response: {response.choices[0].message}")

        # Check if the model wants to call a function
        if hasattr(response.choices[0].message, 'function_call'):
            function_call = response.choices[0].message.function_call
            logger.info(f"Function call requested: {function_call.name}")
            logger.info(f"Function arguments: {function_call.arguments}")

            # Here you would typically implement the actual function call
            mock_weather = {
                "temperature": 22,
                "unit": "celsius",
                "condition": "sunny"
            }

            # Add the function response to the conversation
            messages.append(response.choices[0].message)
            messages.append({
                "role": "function",
                "name": function_call.name,
                "content": json.dumps(mock_weather)
            })

            # Get the final response from the model
            final_response = completion(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.7
            )
            logger.info(f"Final response: {final_response.choices[0].message.content}")

        return response.choices[0].message

    except Exception as e:
        logger.error(f"Error in function calling test: {str(e)}")
        raise


if __name__ == "__main__":
    # test_chatgpt_api()
    test_function_calling()
