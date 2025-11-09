# Environment Setup

Create a `.env` file in the `backend/` directory with the following content:

```
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: base URL for dining scraping (defaults to UMass Dining Locations & Menus)
DINING_BASE_URL=https://umassdining.com/locations-menus

# To use OpenAI instead of Gemini, set provider and API key:
# Options: "gemini" (default) or "openai"
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
# Optional: override default model (defaults to gpt-4o-mini)
# OPENAI_MODEL=gpt-4o-mini
```

To get your Gemini API key:
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Copy the key and paste it in the `.env` file

To get your OpenAI API key:
1. Visit https://platform.openai.com/api-keys
2. Create or copy an existing API key
3. Set `OPENAI_API_KEY` in the `.env` and set `LLM_PROVIDER=openai`

**Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

