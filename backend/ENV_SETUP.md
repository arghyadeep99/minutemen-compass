# Environment Setup

Create a `.env` file in the `backend/` directory with the following content:

```
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: base URL for dining scraping (defaults to UMass Dining Locations & Menus)
DINING_BASE_URL=https://umassdining.com/locations-menus
```

To get your Gemini API key:
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Copy the key and paste it in the `.env` file

**Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

