"""
Test script to check OpenAI API connectivity and get detailed error messages
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_openai_api():
    """Test OpenAI API connectivity"""
    print("Testing OpenAI API Configuration...")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        print("   Please create a .env file with: OPENAI_API_KEY=your_key_here")
        return False
    
    print(f"✓ API Key found (length: {len(api_key)} chars)")
    print(f"  Key starts with: {api_key[:7]}...")
    
    # Try to import and initialize
    try:
        from langchain_openai import ChatOpenAI
        print("✓ langchain_openai imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Failed to import langchain_openai: {e}")
        print("   Run: pip install langchain-openai")
        return False
    
    # Try to create a client
    try:
        model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=api_key
        )
        print("✓ OpenAI client created successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to create OpenAI client: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    # Try a simple test call (optional - comment out if you don't want to use API credits)
    try:
        print("\nTesting API call (this will use API credits)...")
        response = model.invoke("Say 'API test successful' if you can read this.")
        print(f"✓ API call successful!")
        print(f"  Response: {response.content[:100]}")
        return True
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print(f"\n❌ ERROR: API call failed")
        print(f"   Error type: {error_type}")
        print(f"   Error message: {error_msg}")
        
        # Provide specific guidance based on error
        if "API key" in error_msg or "authentication" in error_msg.lower():
            print("\n💡 Suggestion: Your API key may be invalid or expired.")
            print("   Check your OpenAI account and generate a new API key.")
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            print("\n💡 Suggestion: Rate limit exceeded. Wait a moment and try again.")
        elif "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower():
            print("\n💡 Suggestion: Your OpenAI account has insufficient credits.")
            print("   Add credits to your OpenAI account.")
        elif "invalid" in error_msg.lower() and "model" in error_msg.lower():
            print("\n💡 Suggestion: The model 'gpt-4o-mini' may not be available.")
            print("   Check your OpenAI account tier and available models.")
        else:
            print("\n💡 Check the error message above for details.")
        
        return False

if __name__ == "__main__":
    success = test_openai_api()
    sys.exit(0 if success else 1)

