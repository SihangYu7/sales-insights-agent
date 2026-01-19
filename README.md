# 🤖 AI Sales Analytics Agent

> An intelligent sales data analytics assistant powered by OpenAI GPT and LangChain that converts natural language questions into SQL queries and provides data-driven insights.

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange.svg)](https://openai.com)
[![LangChain](https://img.shields.io/badge/LangChain-1.2-purple.svg)](https://langchain.com)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Demo](#demo)
- [Documentation](#documentation)

---

## 🎯 Overview

This project is a complete AI agent system that demonstrates:
- **Text-to-SQL conversion** using LangChain
- **Natural language understanding** with OpenAI GPT-3.5
- **Safe query execution** with SQL injection prevention
- **Multi-step reasoning** with custom tools
- **RESTful API design** with Flask

### What Can It Do?

Ask questions in plain English and get data-driven answers:
- "What are the total sales?"
- "Show me the top 5 products by price"
- "Compare Electronics vs Furniture sales"
- "What's the average price of products in each category?"

---

## ✨ Features

### Module 4: Text-to-SQL Agent
- ✅ Natural language to SQL query conversion
- ✅ Automatic schema injection
- ✅ Query validation (SELECT only)
- ✅ Human-friendly response formatting
- ✅ Support for JOINs, GROUP BY, aggregations

### Module 5: Enhanced Agent with Tools
- ✅ Custom tools: QueryDatabase, GetSchema, Calculate, GetDate
- ✅ Multi-step reasoning capability
- ✅ Better handling of complex questions
- ✅ Tool availability indication

### Security
- ✅ SQL injection prevention
- ✅ Query validation (blocks DROP, DELETE, UPDATE, etc.)
- ✅ Environment variable management
- ✅ API key protection

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (tested on 3.14)
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   cd backend
   ```

2. **Set up virtual environment** (if not already created)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

5. **Run the server**
   ```bash
   python app.py
   ```

   Server will start at `http://localhost:5000`

### Quick Test

```bash
# Test Module 4
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the total sales?"}'

# Test Module 5
curl -X POST http://localhost:5000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 3 products and their average price?"}'
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User / Client                            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask REST API (7 Endpoints)                    │
│                                                              │
│  /api/ask (Module 4)  │  /api/agent (Module 5)              │
└──────────┬─────────────┴──────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐      ┌─────────────────────────┐
│  LangChain           │      │  Custom Tools            │
│  Text-to-SQL Agent   │      │  • QueryDatabase         │
│                      │      │  • GetSchema             │
│  • Schema injection  │      │  • Calculate             │
│  • SQL generation    │      │  • GetDate               │
│  • Query validation  │      └─────────────────────────┘
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│           SQLite Database (sales.db)                         │
│  • 10 Products (Electronics, Furniture, Books)              │
│  • 200 Sales Records (4 regions: N, S, E, W)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📡 API Documentation

### Base URL
```
http://localhost:5000
```

### Endpoints

#### 1. Health Check
```http
GET /
```

**Response:**
```json
{
  "status": "healthy",
  "message": "AI Agent Backend is running! 🚀",
  "modules_completed": ["Module 1", "Module 2", "Module 3", "Module 4", "Module 5"]
}
```

#### 2. Get Products
```http
GET /api/products
```

**Response:**
```json
{
  "count": 10,
  "products": [
    {"id": 1, "name": "Laptop", "category": "Electronics", "price": 999.99},
    ...
  ]
}
```

#### 3. Sales Summary
```http
GET /api/sales/summary
```

**Response:**
```json
{
  "total_sales": 204593.89,
  "total_transactions": 200,
  "by_region": [...],
  "by_category": [...],
  "top_products": [...]
}
```

#### 4. Get Database Schema
```http
GET /api/schema
```

**Response:**
```json
{
  "schema": {
    "database_type": "SQLite",
    "tables": {
      "products": {...},
      "sales": {...}
    }
  }
}
```

#### 5. Execute SQL Query
```http
POST /api/query
Content-Type: application/json

{
  "sql": "SELECT * FROM products LIMIT 3"
}
```

**Response:**
```json
{
  "query": "SELECT * FROM products LIMIT 3",
  "results": [...],
  "row_count": 3
}
```

#### 6. Text-to-SQL Agent (Module 4) ⭐
```http
POST /api/ask
Content-Type: application/json

{
  "question": "What are the total sales?"
}
```

**Response:**
```json
{
  "question": "What are the total sales?",
  "answer": "The answer is: 204,593.89",
  "sql": "SELECT SUM(total) AS total_sales FROM sales;",
  "results": [{"total_sales": 204593.89}],
  "row_count": 1,
  "success": true,
  "module": "Module 4: Text-to-SQL Agent",
  "agent_type": "LangChain SQL Agent"
}
```

#### 7. Enhanced Agent with Tools (Module 5) ⭐
```http
POST /api/agent
Content-Type: application/json

{
  "question": "What are the top 3 products and their average price?"
}
```

**Response:**
```json
{
  "question": "What are the top 3 products and their average price?",
  "answer": "The top 3 products are...",
  "sql": "SELECT name, price FROM products ORDER BY price DESC LIMIT 3;",
  "results": [...],
  "success": true,
  "module": "Module 5: Enhanced Agent with Tools",
  "agent_type": "Tool-Equipped Agent (Module 5)",
  "tools_available": ["QueryDatabase", "GetSchema", "Calculate", "GetDate"]
}
```

---

## 🧪 Testing

### Automated Test Suite

Run the comprehensive test suite:

```bash
# Run all tests
python test_agents.py

# Test Module 4 only
python test_agents.py --module 4

# Test Module 5 only
python test_agents.py --module 5

# Test custom question
python test_agents.py --custom "What are sales in the North region?" --module 4
```

### Manual Testing

```bash
# Simple query
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the total sales?"}'

# Complex query
curl -X POST http://localhost:5000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Compare Electronics vs Furniture average prices"}'
```

### Example Questions

**Module 4 (Simple queries):**
- "What are the total sales?"
- "How many products are in the Electronics category?"
- "Show me the top 5 products by price"
- "What are total sales by region?"
- "What is the average price of products?"

**Module 5 (Complex queries):**
- "What are the top 3 products and their average price?"
- "Compare sales between Electronics and Furniture"
- "What tables are in the database?"
- "Calculate the percentage difference between regions"

---

## 📁 Project Structure

```
ai-agent/
├── backend/
│   ├── app.py                    # Flask API server (7 endpoints)
│   ├── database.py               # SQLAlchemy models & database functions
│   ├── openai_service.py         # OpenAI GPT integration
│   ├── langchain_agent.py        # Module 4: Text-to-SQL agent
│   ├── tools.py                  # Module 5: Custom tools
│   ├── test_agents.py            # Automated test suite
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # Environment variables (API keys)
│   ├── sales.db                  # SQLite database (auto-created)
│   └── venv/                     # Virtual environment
├── README.md                     # This file
├── INTERVIEW_GUIDE.md            # Technical interview preparation
├── MODULE4_TEST_RESULTS.md       # Module 4 validation results
└── PROJECT_COMPLETE.md           # Complete project documentation
```

---

## 🎬 Demo

### Starting the Server
```bash
cd backend
source venv/bin/activate
python app.py
```

**Output:**
```
======================================================================
🚀 AI Agent Backend - Modules 4 & 5: Complete AI Agent
======================================================================

✨ Both Module 4 (Text-to-SQL) and Module 5 (Enhanced Agent) ready!

Endpoints available:
  GET  /                  - Health check
  GET  /api/products      - List all products
  GET  /api/sales/summary - Sales dashboard data
  GET  /api/schema        - Database schema (for AI)
  POST /api/query         - Run SQL query
  POST /api/ask           - 🤖 TEXT-TO-SQL AGENT (Module 4)
  POST /api/agent         - 🧠 ENHANCED AGENT (Module 5)

======================================================================
```

### Live Demo (5 minutes)

1. **Health Check** - Verify server is running
2. **Simple Query** - "What are the total sales?"
3. **Complex Query** - "Show me the top 5 products by price"
4. **Aggregation** - "What are total sales by region?"
5. **Enhanced Agent** - "What are the top 3 products and their average price?"

---

## 📚 Documentation

### For Developers
- **README.md** (this file) - Quick start and API documentation
- **Code Comments** - Extensive inline documentation with learning points

### For Interviews
- **INTERVIEW_GUIDE.md** - Comprehensive technical interview preparation
  - 30-second pitch
  - Code walkthrough
  - Demo script
  - Technical Q&A

- **MODULE4_TEST_RESULTS.md** - Detailed test validation
  - All test cases with results
  - SQL queries generated
  - Performance metrics

- **PROJECT_COMPLETE.md** - Full project overview
  - Architecture diagrams
  - Module progression
  - Learning outcomes
  - Future enhancements

---

## 🔧 Technologies Used

- **Backend:** Flask 3.0.0
- **Database:** SQLite + SQLAlchemy 2.0.45
- **AI/LLM:** OpenAI SDK 2.15.0 (GPT-3.5-Turbo)
- **Agent Framework:** LangChain 1.2.6+
- **Language:** Python 3.14

---

## 📊 Performance

- **Response Time:** 2-5 seconds (includes OpenAI API call)
- **Token Usage:** 200-500 tokens per query
- **Cost:** ~$0.0005 per query (GPT-3.5-Turbo)
- **Database:** 20KB with 200 records

---

## 🛡️ Security

- ✅ SQL injection prevention (forbidden keywords blocked)
- ✅ Query validation (SELECT only)
- ✅ API key management (environment variables)
- ✅ Input sanitization
- ✅ Error handling at all layers

---

## 🚧 Future Enhancements

- [ ] React frontend with chat interface
- [ ] Streaming responses
- [ ] Query caching
- [ ] Rate limiting
- [ ] PostgreSQL migration
- [ ] Docker deployment
- [ ] Grafana dashboards
- [ ] CI/CD pipeline

---
*Last Updated: January 19, 2026*
