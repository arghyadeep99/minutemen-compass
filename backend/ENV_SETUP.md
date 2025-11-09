# Environment Setup

Create a `.env` file in the `backend/` directory with the following content:

```
OPENAI_API_KEY=your_openai_api_key_here
BUS_SCHEDULE_PDF_URL=https://example.com/pvta-schedule.pdf
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: base URL for dining scraping (defaults to UMass Dining Locations & Menus)
DINING_BASE_URL=https://umassdining.com/locations-menus
```

## Required Environment Variables

### OPENAI_API_KEY
To get your OpenAI API key:
1. Visit https://platform.openai.com/api-keys
2. Sign in with your OpenAI account
3. Create a new API key
4. Copy the key and paste it in the `.env` file

### BUS_SCHEDULE_PDF_URLS (Optional)
JSON object mapping route numbers to their PDF URLs. If not set, the system will use the fallback JSON schedule data.

**Format**: JSON string with route numbers as keys and PDF URLs as values.

Example:
```json
BUS_SCHEDULE_PDF_URLS={"30": "https://www.pvta.com/schedules/route-30.pdf", "31": "https://www.pvta.com/schedules/route-31.pdf", "B43": "https://www.pvta.com/schedules/route-b43.pdf"}
```

Or in your `.env` file (single line):
```
BUS_SCHEDULE_PDF_URLS={"30": "https://www.pvta.com/schedules/route-30.pdf", "31": "https://www.pvta.com/schedules/route-31.pdf", "B43": "https://www.pvta.com/schedules/route-b43.pdf"}
```

**Legacy Support**: You can also use `BUS_SCHEDULE_PDF_URL` (singular) for a single PDF containing all routes:
```
BUS_SCHEDULE_PDF_URL=https://www.pvta.com/schedules/all-routes.pdf
```

**Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

