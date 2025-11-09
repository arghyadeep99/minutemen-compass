# Quick Setup Guide

## Prerequisites
- Python 3.8+
- Node.js 16+
- Gemini API key

## Step 1: Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
GEMINI_API_KEY=your_key_here
```

Run backend:
```bash
python main.py
# Or: uvicorn main:app --reload --port 8000
```

## Step 2: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Step 3: Access

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing

Try these queries:
- "Where can I find a quiet study spot?"
- "What's open for food right now?"
- "What mental health resources are available?"
- "What is the next bus from Campus Center to Puffton?"

