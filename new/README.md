# AI Personal Trainer - Agentic API v2.0

Production-grade workout planning system with **LangGraph safety critique loop**, **FastAPI REST API**, and **PostgreSQL persistence**.

> **Note:** This is the new production implementation. For the legacy Streamlit version, see [`../old/`](../old/)

## 🎯 Architecture

### From Monolithic to Microservices
- **Before:** Streamlit app with direct LLM calls and SQLite
- **After:** Decoupled FastAPI backend + LangGraph orchestration + PostgreSQL

### Key Components
1. **LangGraph State Machine**: Multi-agent workflow (Trainer → Physiotherapist)
2. **FastAPI Backend**: RESTful API with dual LLM support (Ollama/OpenAI)
3. **PostgreSQL**: State persistence via `PostgresSaver`
4. **Docker**: Containerized deployment with docker-compose

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Kubernetes cluster for production

### Local Development with Docker Compose

```bash
# 1. Navigate to new implementation
cd new/

# 2. Copy environment template
cp .env.example .env

# 3. (Optional) Edit .env with your API keys
#    - For local: Keep default Ollama settings
#    - For cloud: Add OPENAI_API_KEY

# 4. Start all services
docker-compose up --build

# 5. Wait for services to initialize (~2 minutes for Ollama to pull Mistral)

# 6. Test the API
curl http://localhost:8000/health
```

### API Endpoints

**Base URL:** `http://localhost:8000`

#### 1. Health Check
```bash
GET /health
```

#### 2. Generate Workout Plan
```bash
POST /plan
Content-Type: application/json

{
  "user_profile": {
    "goals": "Build upper body strength and muscle mass",
    "fitness_level": "intermediate",
    "weight": 75.0,
    "age": 28,
    "equipment_available": ["barbell", "dumbbells", "bench"]
  },
  "injury_history": [
    {
      "injury_type": "Rotator cuff strain",
      "date": "2024-03-15",
      "severity": "moderate",
      "notes": "Avoid overhead press for 6 weeks"
    }
  ],
  "thread_id": "user_12345"
}
```

#### 3. Get Conversation History
```bash
GET /history/{thread_id}
```

---

## 🏗️ Project Structure

```
new/
├── app/
│   ├── __init__.py         # Package init (version)
│   ├── auth.py             # JWT authentication utilities
│   ├── database.py         # SQLAlchemy engine & sessions
│   ├── models.py           # Database models (User, Workout, Injury, etc.)
│   ├── schemas.py          # Pydantic models for API validation
│   ├── prompts.py          # LLM prompt templates
│   ├── state.py            # TrainerState TypedDict
│   ├── graph.py            # LangGraph safety critique workflow
│   ├── server.py           # FastAPI server (Ollama mode)
│   ├── server_cloud.py     # FastAPI server (OpenAI mode)
│   └── routers/
│       ├── auth.py         # Auth endpoints (signup/login/me)
│       ├── workouts.py     # Workout CRUD & stats
│       ├── injuries.py     # Injury profile management
│       └── plans.py        # Saved workout plans
├── frontend/
│   ├── app.py              # Streamlit dashboard
│   └── api_client.py       # API client for frontend
├── tests/
│   ├── conftest.py         # Shared pytest fixtures
│   ├── test_schemas.py     # Pydantic validation tests
│   ├── test_graph.py       # Graph logic & routing tests
│   └── test_prompts.py     # Prompt generation tests
├── k8s/
│   ├── deployment.yaml     # Kubernetes manifests
│   └── README.md           # K8s deployment guide
├── Dockerfile              # Multi-stage API build
├── Dockerfile.frontend     # Streamlit frontend build
├── docker-compose.yml      # Full stack orchestration
├── requirements.txt        # Python dependencies
├── seed_data.py            # Database seeder script
├── test_api.py             # Integration tests (requires running server)
├── .env.example            # Environment template
├── .gitignore
└── README.md
```

---

## 🔄 Safety Critique Loop

The system implements a **multi-agent safety validation** workflow:

```
1. Trainer Agent generates workout plan
2. Physiotherapist Agent reviews for injury risks
3. If UNSAFE → Loop back with feedback (max 3 revisions)
4. If SAFE → Return approved plan
```

**Resume Highlight:**
> "Implemented multi-agent safety validation using domain-specific LLM personas for injury risk assessment in fitness applications with LangGraph state orchestration."

---

## 🐳 Deployment

### Quick Start (One Command)

```bash
cd new/
docker-compose up -d
```

**That's it!** The system will:
1. Start PostgreSQL database
2. Start Ollama (auto-downloads Mistral model ~4GB)
3. Start FastAPI backend
4. **Auto-detect GPU** - uses NVIDIA GPU if available, falls back to CPU

Wait 2-3 minutes for first startup, then test:
```bash
curl http://localhost:8000/health
```

### GPU vs CPU Performance

| Mode | LLM Response Time | Auto-Detected |
|------|------------------|---------------|
| **NVIDIA GPU** | 5-15 seconds | ✅ Yes |
| **CPU Only** | 30-90 seconds | ✅ Yes |

> **GPU Requirement:** NVIDIA GPU + [Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

### Kubernetes (Production)

```bash
docker build -t your-registry/ai-trainer:latest .
docker push your-registry/ai-trainer:latest
kubectl apply -f k8s/deployment.yaml
```

See [`k8s/README.md`](k8s/README.md) for details.

---

## 🧪 Testing

### Unit Tests (No external services needed)
```bash
pytest tests/ -v
```

### Integration Tests (Requires running server)
```bash
# Start services first: docker-compose up -d
python test_api.py
```

**Expected:** Unit tests validate schemas, graph logic, and prompts. Integration tests verify API generates workout plans with safety critique loop.

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_URL` | PostgreSQL connection string | `postgresql://...` |
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `mistral` |
| `OPENAI_API_KEY` | OpenAI API key (cloud mode) | - |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o` |

---

## 📊 API Documentation

Interactive API docs available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🛠️ Development

### Run Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL (or use Docker for just the DB)
docker run -d \
  -e POSTGRES_DB=trainer \
  -e POSTGRES_USER=trainer_user \
  -e POSTGRES_PASSWORD=changeme123 \
  -p 5432:5432 \
  postgres:15-alpine

# Set environment variables
export POSTGRES_URL="postgresql://trainer_user:changeme123@localhost:5432/trainer"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="mistral"

# Run server
uvicorn app.server:app --reload
```

---

## 🐛 Troubleshooting

### Issue: "Graph not initialized"
**Solution:** Check if Ollama/OpenAI is reachable:
```bash
docker-compose logs api_local | grep "LLM test"
```

### Issue: "Database connection failed"
**Solution:** Verify PostgreSQL is running:
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Issue: Ollama model not found
**Solution:** Pull the model manually:
```bash
docker-compose exec ollama ollama pull mistral
```

---

## 📝 License

MIT License © 2025

---

## 🙏 Acknowledgments

- **LangGraph** for state orchestration
- **FastAPI** for the excellent web framework
- **Ollama** for local LLM inference
