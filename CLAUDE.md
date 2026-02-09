# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Sales Analytics Agent - A Flask backend demonstrating enterprise AI agent patterns with text-to-SQL capabilities. Features JWT authentication, LangChain middleware (logging, rate limiting, caching), Databricks analytics, and Supabase-backed user sessions.

## Tech Stack

- **Backend:** Flask REST API + SQLAlchemy + LangChain
- **Auth:** JWT (bcrypt + PyJWT)
- **AI:** OpenAI GPT models + LangChain agents
- **Sales Data:** SQLite (dev) / Databricks SQL (production)
- **User/Session Data:** SQLite (dev) / Supabase Postgres (production)

## Build and Run Commands

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py  # Runs on http://localhost:5001
```

## Testing

```bash
# Run Module 4 text-to-SQL agent tests
python backend/llm/text_to_sql.py

# Run Module 5 tool-equipped agent tests (server must be running)
python backend/test_module5.py

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
    ├── /api/ask    → Module 4: Text-to-SQL Chain (llm/text_to_sql.py)
    │                 Single-step: Question → Schema → LLM → SQL → Execute
    │
    └── /api/agent  → Module 5: Tool-Equipped Agent (llm/agent.py)
                      Multi-step ReAct: Reason → Tool → Observe → Repeat
                      Tools: QueryDatabase, GetSchema, Calculate, GetCurrentDate
```

**Key Files:**
- `backend/app.py` - Flask REST API with auth endpoints and agent routes
- `backend/config.py` - Environment config helpers
- `backend/auth/db.py` - Auth DB setup (AUTH_DATABASE_URL)
- `backend/auth/models.py` - User, ChatSession, QueryHistory models
- `backend/auth/service.py` - Auth/session services
- `backend/analytics/connector.py` - Analytics DB connector (SQLite/Databricks)
- `backend/analytics/query.py` - Analytics query helpers
- `backend/analytics/sqlite_db.py` - SQLite analytics models + seed (dev)
- `backend/llm/text_to_sql.py` - Text-to-SQL chain with safety checks
- `backend/llm/agent.py` - Tool-equipped agent (Module 5)
- `backend/llm/openai_client.py` - OpenAI client (Responses API optional)
- `backend/middleware/` - LangChain callbacks, caching, rate limiting

**Databases:**
- **Sales Data:** SQLite (`sales.db`) or Databricks SQL Warehouse - Products (10 records), Sales (200 records)
- **User/Session Data:** SQLite (local) or Supabase Postgres (production) - Users, ChatSessions, QueryHistory

## Environment Variables

```bash
# Backend (.env)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_USE_RESPONSES=false
JWT_SECRET_KEY=your-secret-key  # Generate with: openssl rand -hex 32

# Supabase (optional - for production user/session storage)
AUTH_DATABASE_URL=postgresql://user:pass@host:5432/postgres
# If not set, defaults to SQLite (sqlite:///sales.db)

# Databricks (optional - for production sales data)
ANALYTICS_BACKEND=sqlite  # or databricks
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=your-access-token
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default

# Development: auto-create and seed local SQLite data
DEV_SEED=true
```

## Database Architecture

The project uses separate databases for different concerns:

**Sales Data (analytics/connector.py):**
- **Development:** SQLite (`sales.db`) - no setup required
- **Production:** Databricks SQL Warehouse - set `ANALYTICS_BACKEND=databricks`

**User & Session Data (auth/db.py):**
- **Development:** SQLite (`sales.db`) - shared file locally
- **Production:** Supabase Postgres - set `AUTH_DATABASE_URL`
- Stores: Users, ChatSessions, QueryHistory
- Auto-migrates schema for SQLite (adds session_id column if missing)
