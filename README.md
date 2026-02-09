# 🤖 AI Sales Analytics Agent

> A full-stack AI sales analytics app with a React frontend and Flask backend. Uses LangChain agents, JWT auth, Databricks for analytics, and Supabase for user sessions. Converts natural language questions into SQL queries and returns data-driven insights.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange.svg)](https://openai.com)
[![LangChain](https://img.shields.io/badge/LangChain-1.2+-purple.svg)](https://langchain.com)
[![Databricks](https://img.shields.io/badge/Databricks-SQL-red.svg)](https://databricks.com)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E.svg)](https://supabase.com)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Live Demo](#-live-demo)
- [What I Built](#-what-i-built)

---

## 🎯 Overview

This project demonstrates a production-ready AI agent system featuring:

- **Full-Stack Application** - React frontend + Flask backend
- **Text-to-SQL Conversion** using LangChain
- **JWT Authentication** with access/refresh tokens
- **Dual Database Support** - SQLite (dev) / Databricks (prod)
- **LangChain Middleware** - Logging, rate limiting, caching
- **Production Hosting** - Railway (backend)

### What Can It Do?

Ask questions in plain English and get data-driven answers:
- "What are the total sales?"
- "Show me the top 5 products by revenue"
- "Compare Electronics vs Furniture sales"
- "What's the average price of products in each category?"

---

## ✨ Features

### Frontend
- ✅ React 19 + Vite + TailwindCSS
- ✅ Login/Register with JWT auth
- ✅ Chat UI with session sidebar + editable titles
- ✅ Agent mode toggle (simple SQL vs advanced tools)
- ✅ Sales dashboard (summary + breakdowns)

### Backend - Module 4: Text-to-SQL Agent
- ✅ Natural language to SQL query conversion
- ✅ Automatic schema injection
- ✅ Query validation (SELECT only)
- ✅ Human-friendly response formatting

### Backend - Module 5: Enhanced Agent with Tools
- ✅ Custom tools: QueryDatabase, GetSchema, Calculate, GetDate
- ✅ Multi-step reasoning capability (ReAct pattern)
- ✅ Better handling of complex questions

### Infrastructure
- ✅ JWT authentication with refresh tokens
- ✅ LangChain middleware (logging, metrics, caching, rate limiting)
- ✅ Database abstraction (SQLite ↔ Databricks for sales data)
- ✅ Supabase Postgres for persistent user sessions

### Security
- ✅ SQL injection prevention
- ✅ Password hashing with bcrypt
- ✅ JWT token management
- ✅ Environment variable protection

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite, TailwindCSS |
| **Backend** | Flask 3.0, SQLAlchemy, LangChain |
| **AI/LLM** | OpenAI GPT-3.5-Turbo |
| **Auth** | JWT (bcrypt + PyJWT) |
| **Sales Data** | SQLite (dev) / Databricks SQL (prod) |
| **User Sessions** | SQLite (dev) / Supabase Postgres (prod) |
| **Hosting** | Railway (backend), Vercel (frontend optional) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- OpenAI API key

### Installation

1. **Clone and setup backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Setup environment**
   ```bash
   cp ../.env.example ../.env
   # Edit .env and add your OPENAI_API_KEY and JWT_SECRET_KEY
   ```
   For local SQLite data, set:
   ```bash
   DEV_SEED=true
   ```

3. **Run backend**
   ```bash
   python app.py  # Runs on http://localhost:5001
   ```

4. **Setup frontend** (new terminal)
   ```bash
   cd frontend
   npm install
   npm run dev  # Runs on http://localhost:5173
   ```

5. **Open browser** → http://localhost:5173

### Quick Test

```bash
# Register a user
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login to get token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Ask a question (use token from login response)
curl -X POST http://localhost:5001/api/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"question": "What are the total sales?"}'
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                         │
│  • Login/Register  • Dashboard  • Chat Sessions                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON + JWT
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask REST API                                │
│  • Auth endpoints  • Agent endpoints  • Session endpoints        │
├─────────────────────────────────────────────────────────────────┤
│                    Middleware Layer                              │
│  • Logging  • Metrics  • Rate Limiting  • Caching                │
└──────────┬─────────────────────────────────┬────────────────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────┐           ┌─────────────────────────┐
│  Text-to-SQL Agent  │           │  Tool-Equipped Agent    │
│  (Module 4)         │           │  (Module 5)             │
│  • Schema injection │           │  • QueryDatabase        │
│  • SQL generation   │           │  • GetSchema            │
│  • Query validation │           │  • Calculate            │
└─────────┬───────────┘           │  • GetDate              │
          │                       └─────────────────────────┘
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                 │
├────────────────────────────┬────────────────────────────────────┤
│   Sales Data Connector     │     User/Session Storage           │
│   (analytics/connector.py) │     (auth/db.py)                   │
│   SQLite ↔ Databricks      │     SQLite ↔ Supabase Postgres     │
└────────────────────────────┴────────────────────────────────────┘
```

---

## 📡 API Documentation

### Base URL
- **Local:** `http://localhost:5001`
- **Production:** `https://your-app.up.railway.app`

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login, returns JWT tokens |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/me` | GET | Get current user (requires auth) |

### Agent Endpoints (Protected)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ask` | POST | Text-to-SQL agent (Module 4) |
| `/api/agent` | POST | Enhanced agent with tools (Module 5) |
| `/api/query` | POST | Execute raw SQL SELECT |

### Chat Session Endpoints (Protected)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List user's chat sessions |
| `/api/sessions` | POST | Create new chat session |
| `/api/sessions/<id>` | GET | Get session with messages |
| `/api/sessions/<id>` | PUT | Update session title |

### Data Endpoints (Public)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/products` | GET | List all products |
| `/api/sales/summary` | GET | Sales dashboard data |
| `/api/schema` | GET | Database schema |
| `/api/health` | GET | Database health check |

---

## 🌐 Live Demo

- Backend: https://sales-insights-agent-production-1ec7.up.railway.app
- Frontend: deploy separately (e.g., Vercel) using `frontend/`

**Data stack**
- Sales data: Databricks SQL (`workspace.default`)
- User accounts + chat sessions: Supabase Postgres

SQLite is used only for local development.

## ✅ What I Built

- Full-stack AI analytics app with React + Flask.
- Text‑to‑SQL agent (LangChain) with safe‑query validation.
- Tool‑enabled agent for multi‑step reasoning and calculations.
- JWT auth with refresh tokens and protected endpoints.
- Persistent chat sessions + history stored in Supabase.
- Production data integration using Databricks SQL.

---

## 📁 Project Structure

```
sales-insights-agent/
├── backend/
│   ├── app.py                 # Flask API (auth + agent routes)
│   ├── config.py              # Environment config helpers
│   ├── auth/                  # Supabase-backed auth/session storage
│   │   ├── db.py              # AUTH_DATABASE_URL engine/session
│   │   ├── models.py          # User, ChatSession, QueryHistory
│   │   └── service.py         # Auth + session services
│   ├── analytics/             # Databricks/SQLite analytics layer
│   │   ├── connector.py       # Analytics DB connector
│   │   ├── schema.py          # Dynamic schema discovery
│   │   ├── sql_utils.py       # SQL helpers (qualification, parsing)
│   │   ├── sqlite_db.py       # SQLite models + seed (dev only)
│   │   ├── connection_pool.py # Databricks connection pool
│   │   └── query.py           # run_query/get_schema_info wrappers
│   ├── llm/                   # LLM chain + agent logic
│   │   ├── text_to_sql.py     # Text-to-SQL agent (Module 4)
│   │   ├── agent.py           # Tool-equipped agent (Module 5)
│   │   └── openai_client.py   # OpenAI client (Responses API optional)
│   ├── exceptions.py          # Custom DB exceptions
│   ├── database.py            # Compatibility shim (deprecated)
│   ├── middleware/            # Callbacks + caching + rate limit
│   ├── databricks_setup.sql   # Databricks table creation
│   └── requirements.txt
├── .env.example               # Environment template
├── frontend/
│   ├── src/
│   │   ├── pages/             # Login, Register, Dashboard, Chat
│   │   ├── components/        # ProtectedRoute
│   │   ├── context/           # AuthContext
│   │   └── services/          # API client, auth service
│   ├── package.json
│   └── vite.config.ts
├── CLAUDE.md                  # AI assistant guidance
└── README.md                  # This file
```

---

## 🔧 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=...  # Generate: openssl rand -hex 32

# Optional: model + API mode
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_USE_RESPONSES=false

# Supabase (optional - for persistent sessions in production)
AUTH_DATABASE_URL=postgresql://user:pass@host:5432/postgres
# If not set, defaults to SQLite (sqlite:///sales.db)

# Databricks (optional - for production sales data)
ANALYTICS_BACKEND=sqlite  # or databricks
DATABRICKS_SERVER_HOSTNAME=...
DATABRICKS_HTTP_PATH=...
DATABRICKS_ACCESS_TOKEN=...
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default

# Development: auto-create and seed local SQLite data
DEV_SEED=true

# Frontend (.env)
VITE_API_URL=http://localhost:5001
```

---

## 📊 Example Queries

**Simple Queries (Module 4):**
- "What are the total sales?"
- "How many products are in Electronics?"
- "Show me the top 5 products by price"
- "What are total sales by region?"

**Complex Queries (Module 5):**
- "What are the top 3 products and their average price?"
- "Compare sales between Electronics and Furniture"
- "Calculate the percentage of sales in each region"

---

*Built with LangChain, OpenAI, Flask, Databricks, and Supabase*
