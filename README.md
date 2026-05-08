<div align="center">

# 🔥 Roast My CV

### AI-powered internship readiness tool — upload your CV, get roasted, know your shot.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=for-the-badge)](https://groq.com)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-black?style=for-the-badge)](https://elevenlabs.io)
[![Firecrawl](https://img.shields.io/badge/Firecrawl-Search-orange?style=for-the-badge)](https://firecrawl.dev)

---

## 📹 Demo

[![Roast My CV Demo](https://img.youtube.com/vi/3C7n0WCoGNE/maxresdefault.jpg)](https://youtu.be/3C7n0WCoGNE)

> *Click to watch the full demo*

---

</div>

## What it does

Upload your CV PDF and get a brutally honest AI-powered assessment of your internship chances — backed by real hiring signal research, not just vibes.

| Feature | Description |
|---|---|
| 📄 **CV Analysis** | Parses your PDF and extracts skills, experience, CGPA, and courses automatically |
| 🏢 **Company Verdicts** | Rates each target company as *Realistic*, *Reach*, or *Be honest with yourself* |
| 📊 **Readiness Score** | 0–100 score with a one-line honest take that hits different |
| ✨ **Donald Says Apply Here** | Recommends 6 companies (2 reach / 3 target / 1 safety) based on your actual profile |
| 🔊 **Voice Roast** | ElevenLabs AI voice reads your personalised roast out loud |
| 🎯 **Matches Page** | All recommended companies grouped by tier in one place |

---

## How it works

```
Your CV (PDF)
     ↓
FastAPI extracts text via Claude (Anthropic)
     ↓
Firecrawl searches real hiring signals for each target company
     ↓
Groq (LLaMA 3.3 70B) analyses your profile against the research
     ↓
Structured roast: verdicts + score + tips + recommendations
     ↓
ElevenLabs reads it back to you
```

---

## Tech Stack

- **Backend** — FastAPI (Python 3.11), served with Uvicorn
- **LLM** — Groq API running LLaMA 3.3 70B Versatile (fast + free tier)
- **CV Parsing** — Anthropic Claude API
- **Research** — Firecrawl for real-time web search on company hiring bars
- **Voice** — ElevenLabs TTS (Adam voice, works on free tier)
- **Frontend** — Vanilla HTML/JS with Tailwind CSS, served directly by FastAPI
- **Deployment** — Railway

---

## Local Setup

**Prerequisites:** Python 3.11+, pip

```bash
# Clone
git clone https://github.com/Abhisheksk2005/roast-my-cv.git
cd roast-my-cv

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp backend/.env.example backend/.env
# Fill in your API keys in backend/.env

# Run
python -m uvicorn backend.main:app --reload
```

Open `http://localhost:8000/static/internship.html`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | LLaMA analysis — [console.groq.com](https://console.groq.com) |
| `ANTHROPIC_API_KEY` | ✅ | CV parsing — [console.anthropic.com](https://console.anthropic.com) |
| `FIRECRAWL_API_KEY` | ✅ | Hiring signal research — [firecrawl.dev](https://firecrawl.dev) |
| `ELEVENLABS_API_KEY` | ✅ | Voice roast — [elevenlabs.io](https://elevenlabs.io) |
| `ELEVENLABS_VOICE_ID` | ⚙️ | Default: `pNInz6obpgDQGcFmaJgB` (Adam, free tier) |

---

## Live Demo

🚀 **[roast-my-cv.onrender.com/static/internship.html](https://roast-my-cv.onrender.com/static/internship.html)**

> First load may take ~30 seconds (free tier cold start) — worth the wait.

## Deployment

Deployed on **Render** (free tier). See `RAILWAY.md` for Railway deployment instructions.

[![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

---

<div align="center">

Built by **Abhishek** · [GitHub](https://github.com/Abhisheksk2005)

</div>
