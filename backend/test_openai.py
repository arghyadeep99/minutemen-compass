"""
Simple test script to verify OpenAI API key with gpt-5-mini model
"""
import os
import sys
from dotenv import load_dotenv

# Set UTF-8 encoding for the environment
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Load environment variables
load_dotenv()

def test_openai_api(model_name="gpt-5-mini"):
    """Test OpenAI API connection with specified model"""
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in .env file")
        print("Please make sure you have OPENAI_API_KEY=your_key_here in backend/.env")
        return False
    
    print(f"Found API key: {api_key[:10]}...{api_key[-4:]}")
    
    # Check for non-ASCII characters in API key
    non_ascii_chars = [c for c in api_key if ord(c) >= 128]
    if non_ascii_chars:
        print(f"\nWARNING: API key contains non-ASCII characters: {non_ascii_chars}")
        print("This will cause authentication errors. Please check your .env file.")
        print("OpenAI API keys should only contain ASCII characters.")
        print("\nTo fix:")
        print("1. Go to https://platform.openai.com/api-keys")
        print("2. Create a new API key")
        print("3. Copy it carefully (without any special characters)")
        print("4. Update your backend/.env file")
        return False
    
    print(f"\nTesting OpenAI API with {model_name} model...")
    
    # Try OpenAI client directly first
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print("Sending test message: 'Hello, can you hear me?'")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello, can you hear me?"}],
            temperature=0.7
        )
        
        print("\nSUCCESS! API is working correctly.")
        print(f"Response: {response.choices[0].message.content}")
        print(f"\nYour OpenAI API key is valid and {model_name} model is accessible!")
        return True
        
    except Exception as e:
        error_msg = repr(e)  # Use repr to avoid encoding issues
        print(f"\nERROR: Failed to connect to OpenAI API")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {error_msg[:200]}...")  # Truncate to avoid encoding issues
        
        # Check if it's a model name issue
        error_str = str(e).lower()
        if "model" in error_str or "not found" in error_str or "invalid" in error_str or "does not exist" in error_str:
            print(f"\nModel '{model_name}' might not be available.")
            print("Trying alternative models...")
            
            # Try common model names
            alternative_models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
            for alt_model in alternative_models:
                try:
                    print(f"\nTrying {alt_model}...")
                    alt_response = client.chat.completions.create(
                        model=alt_model,
                        messages=[{"role": "user", "content": "Hello"}],
                        temperature=0.7
                    )
                    print(f"SUCCESS! {alt_model} works! Your API key is valid.")
                    print(f"Sample response: {alt_response.choices[0].message.content[:50]}...")
                    print(f"\nNote: '{model_name}' might not be available. Consider using '{alt_model}' instead.")
                    return True
                except Exception as alt_e:
                    print(f"  {alt_model} failed: {type(alt_e).__name__}")
                    continue
        
        print("\nPossible issues:")
        print("1. Invalid API key")
        print("2. Insufficient API credits")
        print("3. Model name might not be available")
        print("4. Network connectivity issues")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI API Key Test Script")
    print("=" * 60)
    print()
    
    success = test_openai_api()
    
    print()
    print("=" * 60)
    if success:
        print("Test completed successfully! ✅")
    else:
        print("Test failed. Please check the errors above. ❌")
    print("=" * 60)

