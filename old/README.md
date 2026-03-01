# 💪 AI Personal Trainer

An intelligent fitness application that generates **personalized, injury-safe workout plans** using multi-agent LLM orchestration. Built with **LangGraph**, **FastAPI**, and **Streamlit**.

> A Trainer agent drafts your plan → A Physiotherapist agent reviews it for safety → Unsafe exercises are automatically revised.

---

## ✨ Features

- **Multi-Agent Safety Loop** — LangGraph state machine orchestrates Trainer ↔ Physiotherapist agents with automatic revision cycles (up to 3x)
- **Natural Language Workout Logging** — Log workouts in plain English, parsed by LLM
- **Injury-Aware Planning** — Active injuries are cross-referenced against every exercise
- **Analytics Dashboard**
  ![Analytics](old/assets/analytics.png) — Training volume, cardio progress, personal records, and streak tracking
- **Dual LLM Support** — Local (Ollama/Mistral) or Cloud (OpenAI GPT-4o)
- **Full REST API** — Decoupled FastAPI backend with Swagger docs
- **JWT Authentication** — Secure user accounts with Argon2 password hashing
- **Production-Ready** — Docker Compose, Kubernetes manifests, health checks, LLM metrics logging

---

## 🏗️ Architecture

```
┌──────────────┐     REST API     ┌──────────────────────────────────────┐
│   Streamlit  │ ◄──────────────► │           FastAPI Server             │
│   Frontend   │                  │                                      │
│  (port 8501) │                  │  ┌──────────┐    ┌──────────────┐   │
└──────────────┘                  │  │  Trainer  │───►│Physiotherapist│   │
                                  │  │  Agent    │◄───│   Agent       │   │
                                  │  └──────────┘    └──────────────┘   │
                                  │       LangGraph State Machine        │
                                  └──────────┬───────────────────────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              ▼              ▼              ▼
                        ┌──────────┐  ┌──────────┐  ┌──────────┐
                        │PostgreSQL│  │  Ollama   │  │ OpenAI   │
                        │   (DB)   │  │ (Local)   │  │ (Cloud)  │
                        └──────────┘  └──────────┘  └──────────┘
```

---

## 📂 Project Structure

```
AI_Personal_Trainer-main/
├── old/                    # v1: Streamlit + SQLite prototype
│   ├── app.py              # Streamlit app (Ollama mode)
│   ├── app2.py             # Streamlit app (HuggingFace mode)
│   ├── db.py               # SQLite database
│   └── llm.py              # LLM client
│
├── new/                    # v2: Production-grade agentic API
│   ├── app/
│   │   ├── server.py       # FastAPI application
│   │   ├── graph.py        # LangGraph state machine
│   │   ├── state.py        # State schema (TypedDict)
│   │   ├── prompts.py      # Centralized LLM prompts
│   │   ├── auth.py         # JWT authentication
│   │   ├── database.py     # SQLAlchemy engine/session
│   │   ├── models.py       # Database models (User, Workout, Injury, Plan)
│   │   ├── schemas.py      # Pydantic request/response models
│   │   └── routers/
│   │       ├── auth.py     # /auth/signup, /auth/login, /auth/me
│   │       ├── workouts.py # /workouts CRUD + stats
│   │       ├── injuries.py # /injuries CRUD + active filter
│   │       └── plans.py    # /plans CRUD + stats
│   │
│   ├── frontend/
│   │   ├── app.py          # Streamlit UI (6 tabs)
│   │   └── api_client.py   # HTTP client for backend
│   │
│   ├── k8s/                # Kubernetes deployment manifests
│   ├── docker-compose.yml  # Full stack: Postgres + Ollama + API + Frontend
│   ├── Dockerfile          # Multi-stage API build
│   └── Dockerfile.frontend # Frontend container
│
└── README.md               # This file
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- (Optional) NVIDIA GPU + [Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) for faster LLM inference

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/AI_Personal_Trainer.git
cd AI_Personal_Trainer/new

# Copy and edit environment variables
cp .env.example .env
```

**Required:** Generate a JWT secret key and add it to `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Paste the output as JWT_SECRET_KEY in .env
```

### 2. Launch with Docker Compose

```bash
docker-compose up --build -d
```

This starts 4 services:
| Service     | Port  | Description                    |
|-------------|-------|--------------------------------|
| **API**     | 8000  | FastAPI + Swagger at `/docs`   |
| **Frontend**| 8501  | Streamlit dashboard            |
| **Postgres**| 5432  | Database                       |
| **Ollama**  | 11434 | Local LLM (auto-pulls Mistral) |

### 3. Open the App

- **Dashboard:** [http://localhost:8501](http://localhost:8501)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ⚙️ Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | ✅ Yes | — | Secret for signing JWT tokens |
| `DB_PASSWORD` | No | `changeme123` | PostgreSQL password |
| `CORS_ORIGINS` | No | `http://localhost:8501,http://frontend:8501` | Allowed frontend origins |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `mistral` | LLM model name |
| `OPENAI_API_KEY` | No | — | OpenAI key (cloud mode) |
| `POSTGRES_URL` | No | Auto-generated | Full PostgreSQL connection string |

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/signup` | ❌ | Create account |
| `POST` | `/auth/login` | ❌ | Get JWT token |
| `GET` | `/auth/me` | ✅ | Current user info |
| `POST` | `/plan` | ❌ | Generate workout plan (LangGraph) |
| `GET` | `/history/{thread_id}` | ❌ | Get conversation history |
| `POST` | `/workouts` | ✅ | Log a workout |
| `GET` | `/workouts` | ✅ | Get workout history |
| `GET` | `/workouts/stats` | ✅ | Dashboard statistics |
| `POST` | `/injuries` | ✅ | Add injury |
| `GET` | `/injuries/active` | ✅ | Get active injuries |
| `POST` | `/plans` | ✅ | Save generated plan |
| `GET` | `/health` | ❌ | Health check |
| `GET` | `/metrics/llm/summary` | ❌ | LLM performance metrics |

---

## 🧪 Testing

```bash
cd new/

# Run API tests
python test_api.py

# Run comprehensive tests
python test_comprehensive.py

# Run local integration tests
python test_local.py
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Orchestration** | LangGraph (StateGraph, conditional edges, checkpointing) |
| **API** | FastAPI, Pydantic v2, Uvicorn |
| **Database** | PostgreSQL, SQLAlchemy 2.0 |
| **Auth** | JWT (python-jose), Argon2 password hashing |
| **LLM** | Ollama (Mistral) / OpenAI API |
| **Frontend** | Streamlit, Plotly |
| **Deployment** | Docker, Docker Compose, Kubernetes |

---

## 🕰️ Legacy Version (v1 / `old` directory)

> **Note:** The following documentation applies to the original Streamlit implementation found in the `/old` folder.

An AI-powered personal trainer built with **Streamlit**, supporting **workout logging, analytics, and AI-driven coaching**.  
You can run it in **two modes**:
- **Local (`app.py`)** → Runs on your machine using [Ollama](https://ollama.ai) with the `mistral` model.  
- **Cloud (`app2.py`)** → Uses the Hugging Face Inference API (no local model needed).  

### 🚀 Legacy Features
- **Workout Logging**
  ![Workout Logging](old/assets/workout_logging.png)  
  - Input workouts in plain English (e.g., *"10 pushups, bench press 50kg x 3 sets, 5 km run in 25 min"*).  
  - Supports **strength** (sets, reps, weight) and **cardio** (distance, duration).  
  - Automatic parsing and structured storage.  

- **Authentication System**
  ![Login](old/assets/login.png)  
  - Sign up & log in with username + password (securely hashed).  
  - Each user has isolated workout history.  

- **Analytics Dashboard**
  ![Analytics](old/assets/analytics.png)  
  - Training split (strength vs cardio sessions).  
  - **Strength progress** via *training volume* (sets × reps × weight).  
  - **Cardio progress** via *distance* or *pace (min/km)* toggle.  
  - Personal Records (PRs): best lifts, longest runs, fastest times.  

- **AI Coach**
  ![AI Coach](old/assets/ai_coach.png)  
  - Training progression recommendations.  
  - Nutrition guidance.  
  - Safe tips for injury prevention.  
  - Exercise form corrections.  
  - Encouraging, concise responses.  

- **Database Seeding**  
  - Pre-loads sample workouts for quick testing (`seed_db.py`).  

### 📦 Legacy Installation

```bash
cd old/

# Install dependencies
pip install -r requirements.txt
```

### 🔑 Cloud Mode (Hugging Face)

1. Get a Hugging Face API key: [Generate here](https://huggingface.co/settings/tokens).  
2. Add it to `.streamlit/secrets.toml`:
   ```toml
   HUGGINGFACE_API_KEY="your_key_here"
   ```
3. Run:
   ```bash
   streamlit run app2.py
   ```

### 🖥️ Local Mode (Ollama + Mistral)

1. Install [Ollama](https://ollama.ai).  
2. Pull the mistral model:
   ```bash
   ollama pull mistral
   ```
3. Run:
   ```bash
   streamlit run app.py
   ```

### 🔧 Database

- Uses SQLite (`trainer.db`).  
- Tables auto-created with `init_db()`.  
- To seed with sample workouts:
  ```bash
  python seed_db.py
  ```
- Default test user:
  ```
  Username: testuser
  Password: password123
  ```

### 📊 Example Analytics
![Progress Over Time](old/assets/progress.png)

- **Strength** → Training volume trend (kg × reps × sets).  
- **Cardio** → Distance or Pace toggle.  
- **Split** → Strength vs cardio sessions this week.  
- **PRs** → Highest weights, longest runs, fastest paces.  

### 🙌 Legacy Notes

- Local mode requires Ollama installed separately.  
- Hugging Face mode may be rate-limited on free API keys.  
- Extendable: add new exercise types, integrate wearables, or connect external APIs.  

---

## 📜 License

MIT License © 2025
