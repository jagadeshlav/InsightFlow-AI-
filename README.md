# InsightFlow AI — Document Q&A RAG Web App

Upload any document (PDF, TXT, DOCX) and ask questions about it. Get AI-powered answers with source citations using Retrieval Augmented Generation (RAG).

**Live:** [https://www.insightflowai.online](https://www.insightflowai.online)
**App:** [https://www.insightflowai.online/app/](https://www.insightflowai.online/app/)

---

## Features

- **Document Q&A** — Upload and chat with your documents instantly
- **Multi-LLM Support** — Choose from Claude, Gemini, Qwen (TokenRouter), OpenRouter models
- **Free Default Model** — No API key needed to try (`qwen/qwen3.8-max-free` via TokenRouter)
- **Pre-indexed Samples** — Try instantly with demo documents, no upload wait
- **Source Citations** — See which document chunks the AI used for its answer
- **Privacy-First** — API keys used per-request only, never stored
- **Typewriter Effect** — Smooth word-by-word answer reveal
- **Responsive Design** — Works on desktop and mobile

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────────┐
│  GitHub Pages       │  API   │  Render (Free Tier)          │
│  (Frontend)         │───────→│  FastAPI Backend              │
│                     │        │                              │
│  index.html         │        │  ┌─── Upload ─────────────┐ │
│  app/index.html     │        │  │ Parse → Chunk → Embed  │ │
│  assets/css+js      │        │  │ (Gemini Embeddings)    │ │
│                     │        │  └────────────────────────┘ │
│  insightflowai.     │        │  ┌─── Chat ───────────────┐ │
│  online             │        │  │ Retrieve → Prompt → LLM│ │
│                     │        │  │ (Multi-provider)       │ │
└─────────────────────┘        │  └────────────────────────┘ │
                               │  ChromaDB (in-memory)        │
                               └──────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript (vanilla — no framework, no build step) |
| Backend | Python FastAPI |
| Embeddings | Google Gemini (`gemini-embedding-001`, free tier) |
| Vector Store | ChromaDB (ephemeral, in-memory per session) |
| LLM | Multi-provider: TokenRouter, Anthropic, Google, OpenRouter |
| Deployment | GitHub Pages (frontend) + Render free tier (backend) |
| Testing | pytest + FastAPI TestClient (43 tests) |

---

## Project Structure

```
InsightFlow-AI-/
├── index.html              Landing page (GitHub Pages root)
├── privacy.html            Privacy policy
├── terms.html              Terms of service
├── CNAME                   Custom domain config
├── app/
│   └── index.html          RAG app page
├── assets/
│   ├── css/
│   │   ├── common.css      Shared design system
│   │   ├── landing.css     Landing page styles
│   │   └── app.css         App page styles
│   └── js/
│       ├── config.js       API URL & provider config
│       └── app.js          App interaction logic
├── backend/
│   ├── app/
│   │   ├── main.py         FastAPI app & endpoints
│   │   ├── config.py       Environment settings
│   │   ├── schemas.py      Pydantic request/response models
│   │   ├── session_store.py Session management
│   │   ├── rag_engine.py   Parse, chunk, embed, query
│   │   ├── llm_factory.py  Multi-provider LLM builder
│   │   └── sample_loader.py Pre-indexed samples
│   ├── samples/            Demo documents
│   ├── tests/              43 automated tests
│   ├── requirements.txt    Python dependencies
│   ├── Procfile            Render start command
│   └── .env.example        Environment template
├── render.yaml             Render deployment blueprint
├── BUILD_LOG.md            Build journal (Tenglish + One Piece)
├── FUTURE_ENHANCEMENTS.md  Roadmap
└── .gitignore
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/upload` | Upload document (PDF/TXT/DOCX, max 10MB) |
| `POST` | `/api/chat` | Ask question about uploaded document |
| `DELETE` | `/api/sessions/{id}` | Delete a session |
| `GET` | `/api/samples` | List pre-indexed sample documents |
| `POST` | `/api/samples/{id}/chat` | Chat with a sample document |

---

## Local Development

### Prerequisites
- Python 3.11+
- Google API Key (free tier — for embeddings)
- TokenRouter API Key (free models available)

### Backend Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
cp .env.example .env            # Fill in your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend
Open `app/index.html` in your browser, or use VS Code Live Server extension (port 5500).

Update `assets/js/config.js` → `API_BASE_URL` to `http://127.0.0.1:8000` for local development.

### Running Tests
```bash
cd backend
pytest tests/ -v
```

---

## Deployment

### Frontend (GitHub Pages)
Already configured via `CNAME` file. Push to `main` branch → auto-deploys to `insightflowai.online`.

### Backend (Render)
1. Connect this repo to Render
2. Create a new Web Service
3. Set Root Directory: `backend`
4. Set Build Command: `pip install -r requirements.txt`
5. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
6. Add environment variables: `GOOGLE_API_KEY`, `TOKENROUTER_API_KEY`
7. Update `assets/js/config.js` with your Render URL

Or use the `render.yaml` Blueprint for one-click deploy.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key (embeddings, free tier) |
| `TOKENROUTER_API_KEY` | Yes | TokenRouter API key (default free model) |

---

## Interview Demo Flow

1. Open `https://insightflowai.online` → Landing page
2. Click "Try Now — Free" → App page
3. Click "One Piece" sample card → instant (no upload wait!)
4. Ask: "Who is Luffy?" → See answer with source chunks + typewriter effect
5. Ask: "What is Shanks' promise?" → See different chunks retrieved
6. Show "Change Model" feature
7. Show "Upload Your Own" with a test PDF
8. Explain architecture: GitHub Pages + Render + Gemini + ChromaDB + Multi-LLM

---

## MVP Limitations

- Sessions are in-memory only (Render restart = re-upload needed)
- Single backend worker (no horizontal scaling)
- No user authentication or persistent chat history
- Typewriter effect is frontend-only (not real streaming)
- One pre-indexed sample (One Piece story)
- ~60 second cold start on first request (Render free tier)

See `FUTURE_ENHANCEMENTS.md` for the roadmap.

---

## License

MIT
