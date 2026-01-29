# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Sales Analytics Agent - A full-stack application with React frontend and Flask backend demonstrating enterprise AI agent patterns with text-to-SQL capabilities. Features JWT authentication, LangChain middleware (logging, rate limiting, caching), and Docker deployment.

## Tech Stack

- **Frontend:** React 18 + TypeScript + Vite + TailwindCSS
- **Backend:** Flask REST API + SQLAlchemy + LangChain
- **Auth:** JWT (bcrypt + PyJWT)
- **AI:** OpenAI GPT-3.5-Turbo + LangChain agents
- **Sales Data:** SQLite (dev) / Databricks SQL (production)
- **User/Session Data:** SQLite (dev) / Supabase Postgres (production)
- **Deployment:** Docker + Railway

## Build and Run Commands

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py  # Runs on http://localhost:5001

# Frontend (separate terminal)
cd frontend
npm install
npm run dev    # Runs on http://localhost:5173
```

## Testing

```bash
# Run Module 4 text-to-SQL agent tests
python backend/langchain_agent.py

# Run Module 5 tool-equipped agent tests
python backend/test_module5.py
python backend/tools.py

# Test API endpoints with curl (requires JWT token)
# 1. Register and login to get token
curl -X POST http://localhost:5001/api/auth/register -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password123"}'
curl -X POST http://localhost:5001/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password123"}'

# 2. Use token in authenticated requests
curl -X POST http://localhost:5001/api/ask -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d '{"question":"What are the total sales?"}'
curl -X POST http://localhost:5001/api/agent -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d '{"question":"What are the top 3 products?"}'
```

## Architecture

```
Flask API (app.py)
    ├── /api/ask    → Module 4: Text-to-SQL Chain (langchain_agent.py)
    │                 Single-step: Question → Schema → LLM → SQL → Execute
    │
    └── /api/agent  → Module 5: Tool-Equipped Agent (tools.py)
                      Multi-step ReAct: Reason → Tool → Observe → Repeat
                      Tools: QueryDatabase, GetSchema, Calculate, GetCurrentDate
```

**Key Files:**
- `backend/app.py` - Flask REST API with auth endpoints and agent routes
- `backend/auth.py` - JWT authentication service (bcrypt + PyJWT)
- `backend/database.py` - SQLAlchemy models (Product, Sale, User, QueryHistory, ChatSession)
- `backend/db_connector.py` - Database abstraction layer (SQLite/Databricks factory pattern)
- `backend/langchain_agent.py` - LangChain text-to-SQL chain with query validation
- `backend/tools.py` - Custom LangChain tools and ReAct agent (up to 5 reasoning steps)
- `backend/middleware/` - LangChain callbacks (logging, metrics, rate limiting, caching)
- `frontend/src/pages/Chat.tsx` - Claude-like chat interface with session sidebar

**Databases:**
- **Sales Data:** SQLite (`sales.db`) or Databricks SQL Warehouse - Products (10 records), Sales (200 records)
- **User/Session Data:** SQLite (local) or Supabase Postgres (production) - Users, ChatSessions, QueryHistory

## API Endpoints

### Authentication (Public)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/register` | POST | User registration |
| `/api/auth/login` | POST | User login, returns JWT tokens |
| `/api/auth/refresh` | POST | Refresh expired access token |
| `/api/auth/me` | GET | Get current user info (requires auth) |

### Agent Endpoints (Protected - require JWT)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ask` | POST | Text-to-SQL agent (Module 4) |
| `/api/agent` | POST | Enhanced agent with tools (Module 5) |
| `/api/query` | POST | Execute raw SQL SELECT |

### Chat Session Endpoints (Protected - require JWT)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/sessions` | GET | List user's chat sessions |
| `/api/sessions` | POST | Create new chat session |
| `/api/sessions/<id>` | GET | Get session with messages |
| `/api/sessions/<id>` | PUT | Update session title |

### Data Endpoints (Public)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/products` | GET | List products |
| `/api/sales/summary` | GET | Sales dashboard |
| `/api/schema` | GET | Database schema |
| `/api/health` | GET | Database health check (returns db type) |

## LangChain Middleware

Custom callback handlers in `backend/middleware/`:

- **LoggingCallbackHandler** - Tracks LLM/tool events with user context
- **MetricsCallbackHandler** - Response times, token usage, cost estimates
- **UserContextCallbackHandler** - Per-user tracking and personalization
- **Rate Limiting** - Per-user limits (InMemoryRateLimiter)
- **Response Caching** - In-memory cache with TTL

## Security

- JWT authentication with access/refresh tokens
- SQL queries validated via `is_safe_sql()` - only SELECT allowed
- Math calculations use AST parsing, not eval()
- Passwords hashed with bcrypt (12 rounds)
- Environment variables: `OPENAI_API_KEY`, `JWT_SECRET_KEY`

## Frontend Development

```bash
cd frontend
npm install
npm run dev     # Development server at http://localhost:5173
npm run build   # Production build
```

## Docker Deployment

```bash
# Create .env file from example
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and JWT_SECRET_KEY

# Build and run all services
docker-compose up --build

# Services:
# - Backend API: http://localhost:5001
# - Frontend (nginx): http://localhost:80
#   - Serves React app
#   - Proxies /api/* requests to backend

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build --force-recreate
```

### Railway Deployment (Combined Container)

Uses `Dockerfile.railway` for a single container deployment:

```bash
# Build and test locally first
docker build -f Dockerfile.railway -t sales-agent .
docker run -p 80:80 \
  -e OPENAI_API_KEY=your-key \
  -e JWT_SECRET_KEY=your-secret \
  sales-agent

# Test at http://localhost
```

**Deploy to Railway:**
1. Push to GitHub repository
2. Create new Railway project from repo
3. Set Dockerfile path to `Dockerfile.railway`
4. Configure environment variables in Railway dashboard:
   - `OPENAI_API_KEY`
   - `JWT_SECRET_KEY`
   - `USE_DATABRICKS=false` (or `true` with Databricks config)
5. Railway auto-assigns subdomain: `your-app.up.railway.app`

**Health Check:** `GET /api/health` - Returns database status and type

## Environment Variables

```bash
# Backend (.env)
OPENAI_API_KEY=your-openai-key
JWT_SECRET_KEY=your-secret-key  # Generate with: openssl rand -hex 32

# Supabase (optional - for production user/session storage)
DATABASE_URL=postgresql://user:pass@host:5432/postgres  # Supabase connection string
# If not set, defaults to SQLite (sqlite:///sales.db)

# Databricks (optional - for production sales data)
USE_DATABRICKS=false  # Set to true to use Databricks instead of SQLite
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=your-access-token
DATABRICKS_CATALOG=workspace  # or "main" depending on your setup
DATABRICKS_SCHEMA=default

# Frontend (frontend/.env)
VITE_API_URL=http://localhost:5001  # For local development
# Leave empty for Docker/Railway (nginx proxies /api/)
```

## Database Architecture

The project uses separate databases for different concerns:

**Sales Data (db_connector.py):**
- **Development:** SQLite (`sales.db`) - no setup required
- **Production:** Databricks SQL Warehouse - set `USE_DATABRICKS=true`

**User & Session Data (database.py):**
- **Development:** SQLite (`sales.db`) - shared with sales data locally
- **Production:** Supabase Postgres - set `DATABASE_URL` connection string
- Stores: Users, ChatSessions, QueryHistory
- Auto-migrates schema for SQLite (adds session_id column if missing)

**Chat Sessions:**
- Claude-like interface with persistent conversation history
- Sessions auto-titled from first question
- Messages grouped by session for easy navigation
