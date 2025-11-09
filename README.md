# Minutemen Compass

A chat-based AI assistant that answers campus-specific questions for UMass Amherst students, staff, and faculty, and can take actions via tools (like finding buses, study spaces, resources) instead of just giving generic answers.

## 🎯 Project Overview

**Minutemen Compass** is like ChatGPT, but actually understands UMass life and does real tasks. Built for HackUMass with a focus on Ethical AI and using the Gemini API.

## ✨ Features

### MVP Features
- **Conversational campus Q&A**: Chat interface powered by Google Gemini
- **Tool-based actions**: 
  - Find study spots (by location, noise level, group size)
  - Get dining options (by time, dietary preferences)
  - Access support resources (mental health, academic, financial)
  - Check PVTA bus schedules
  - Course information (placeholder)
  - Facility information (placeholder)
  - Report facility issues (placeholder)
- **Ethical guardrails**: Safety checks for harmful requests with appropriate campus resource suggestions
- **Simple web UI**: Clean chat interface with quick action chips

### Stretch Features (Future)
- Multi-agent mode with different personas
- User login and favorites
- Analytics dashboard

## 🛠️ Tech Stack

- **Frontend**: React + Vite + TailwindCSS
- **Backend**: FastAPI (Python)
- **AI**: Google Gemini API (gemini-1.5-flash)
- **Data Storage**: JSON files + SQLite for logging

## 📁 Project Structure

```
.
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── gemini_client.py        # Gemini API integration
│   ├── tools.py                # Tool registry and implementations
│   ├── safety_checker.py      # Ethical guardrails
│   ├── requirements.txt       # Python dependencies
│   └── data/
│       ├── study_spaces.json   # Study space data
│       ├── dining.json         # Dining options data
│       ├── resources.json      # Campus resources data
│       ├── bus_schedules.json  # PVTA bus schedules
│       └── logs.db             # SQLite database for logs
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── MessageList.jsx
│   │   │   ├── MessageInput.jsx
│   │   │   └── QuickActions.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

5. Run the backend server:
```bash
python main.py
# Or with uvicorn directly:
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 📝 API Endpoints

### Chat
- `POST /api/chat` - Main chat endpoint
  ```json
  {
    "message": "Where can I find a quiet study spot?",
    "session_id": "optional"
  }
  ```

### Direct Tool Endpoints
- `GET /api/study-spots?location=Central&noise_preference=quiet&group_size=1-3`
- `GET /api/dining?time_now=20:00&dietary_pref=vegetarian`
- `GET /api/resources?topic=mental_health`
- `GET /api/bus?origin=Campus Center&destination=Puffton`

### Admin
- `GET /api/logs?limit=50` - View query logs

## 🎨 Usage Examples

### Student Use Cases
- "Where can I find a quiet study spot near LGRC right now?"
- "What is a good place to get food after 9 pm on campus?"
- "I am overwhelmed and stressed. What campus resources can I use?"
- "How do I contact the financial aid office?"

### Faculty/Staff Use Cases
- "How can I quickly share office hours and location with my students?"
- "What campus guidelines apply if a student asks for disability accommodations?"

### General Campus
- "The bathroom near my classroom is broken. How do I report this?"
- "What is the next bus from Campus Center to Puffton?"

## 🔒 Ethical Guardrails

The system includes safety checks that:
- Detect and refuse harmful requests (self-harm, harassment, cheating, violence)
- Provide appropriate campus resources instead
- Log flagged queries (without PII) for analysis

## 🏆 HackUMass Categories

- **[Ethical AI] Most Impactful AI Hack** (primary)
- **Best Use of Gemini API**
- **Best Use of AI powered by Reach Capital** (future of learning / campus life)

## 📄 License

See LICENSE file for details.

## 🤝 Contributing

This is a HackUMass project. Contributions welcome!

## 🙏 Acknowledgments

- UMass Amherst for campus information
- Google Gemini API
- HackUMass organizers
