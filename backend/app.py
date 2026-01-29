"""
AI Agent Backend - Modules 1-5: Full AI Agent System
====================================================
Now your API has an enhanced AI agent with tools!

NEW IN MODULE 5:
- Tool-equipped agent with multi-step reasoning
- Custom tools: QueryDatabase, GetSchema, Calculate, GetDate
- Conversation memory for context
- ReAct pattern (Reasoning + Acting)

PROGRESSION:
- Module 1-2: Flask API + Database
- Module 3: Basic OpenAI integration
- Module 4: Text-to-SQL agent (single-step)
- Module 5: Enhanced agent with tools (multi-step reasoning)
"""

import os
from datetime import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from database import init_db, seed_database, run_query, get_schema_info, get_db, Product, Sale, save_query_history, get_user_query_history, create_chat_session, get_user_sessions, get_session_messages, get_session_by_id, update_session_title
from openai_service import ai_sales_assistant
from langchain_agent import text_to_sql_agent
from tools import agent_with_tools  # Module 5 - Now enabled!
from auth import (
    create_user, authenticate_user, refresh_access_token,
    get_user_by_id, require_auth, optional_auth
)
from middleware.rate_limiter import rate_limit, check_rate_limit, get_rate_limiter
from middleware.cache import get_response_cache
from db_connector import get_database_connector

# Create the Flask application
app = Flask(__name__)

# Configure CORS for frontend origins (including Railway deployment)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",  # Vite dev server
            "http://localhost:80",    # Docker frontend
            "http://localhost",       # Docker frontend (no port)
            "http://127.0.0.1:5173",  # Alternative localhost
            "http://127.0.0.1",       # Alternative localhost
        ],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Add Railway domains dynamically if deployed
@app.after_request
def add_cors_headers(response):
    """Add CORS headers for Railway deployment."""
    origin = request.headers.get('Origin', '')
    # Allow any Railway subdomain
    if origin and ('.up.railway.app' in origin or '.railway.app' in origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# =============================================================================
# Initialize database when app starts
# =============================================================================
print("🗄️  Initializing database...")
init_db()
seed_database()


# =============================================================================
# ROUTE 1: Health Check
# =============================================================================
@app.route('/', methods=['GET'])
def health_check():
    """Check if the server is running"""
    return jsonify({
        "status": "healthy",
        "message": "AI Agent Backend is running! 🚀",
        "modules_completed": [
            "Module 1: Flask API",
            "Module 2: Database",
            "Module 3: OpenAI Integration",
            "Module 4: Text-to-SQL Agent",
            "Module 5: Enhanced Agent with Tools",
            "Authentication: JWT-based auth"
        ]
    })


@app.route('/api/health', methods=['GET'])
def database_health():
    """
    Check database connectivity and return health status.

    Returns database type (sqlite/databricks) and connection status.
    Useful for monitoring and deployment verification.

    Try it: GET http://localhost:5001/api/health
    """
    try:
        connector = get_database_connector()
        is_healthy = connector.is_healthy()
        db_type = connector.get_db_type()

        status_code = 200 if is_healthy else 503
        return jsonify({
            "status": "healthy" if is_healthy else "unhealthy",
            "database_type": db_type,
            "timestamp": datetime.utcnow().isoformat(),
            "use_databricks": os.getenv("USE_DATABRICKS", "false").lower() == "true"
        }), status_code
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# =============================================================================
# AUTH ROUTES
# =============================================================================
@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword",
        "name": "John Doe"  (optional)
    }

    Try it:
    curl -X POST http://localhost:5000/api/auth/register \
         -H "Content-Type: application/json" \
         -d '{"email": "test@example.com", "password": "password123", "name": "Test User"}'
    """
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    result = create_user(email, password, name)

    if result['success']:
        return jsonify({
            "message": "User registered successfully",
            "user": result['user']
        }), 201
    else:
        return jsonify({"error": result['error']}), 400


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Authenticate a user and return JWT tokens.

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }

    Returns:
    {
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "user": {...}
    }

    Try it:
    curl -X POST http://localhost:5000/api/auth/login \
         -H "Content-Type: application/json" \
         -d '{"email": "test@example.com", "password": "password123"}'
    """
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    result = authenticate_user(email, password)

    if result['success']:
        return jsonify({
            "access_token": result['access_token'],
            "refresh_token": result['refresh_token'],
            "user": result['user']
        })
    else:
        return jsonify({"error": result['error']}), 401


@app.route('/api/auth/refresh', methods=['POST'])
def refresh():
    """
    Refresh an expired access token using a refresh token.

    Request body:
    {
        "refresh_token": "eyJ..."
    }

    Returns:
    {
        "access_token": "eyJ..."
    }

    Try it:
    curl -X POST http://localhost:5000/api/auth/refresh \
         -H "Content-Type: application/json" \
         -d '{"refresh_token": "your-refresh-token"}'
    """
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    result = refresh_access_token(refresh_token)

    if result['success']:
        return jsonify({
            "access_token": result['access_token']
        })
    else:
        return jsonify({"error": result['error']}), 401


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    Get the current authenticated user's information.

    Requires: Authorization header with Bearer token

    Try it:
    curl -X GET http://localhost:5000/api/auth/me \
         -H "Authorization: Bearer your-access-token"
    """
    user = get_user_by_id(g.user_id)

    if user:
        return jsonify({
            "user": user.to_dict()
        })
    else:
        return jsonify({"error": "User not found"}), 404


# =============================================================================
# ROUTE 2: Get All Products
# =============================================================================
@app.route('/api/products', methods=['GET'])
def get_products():
    """
    Returns all products in the database.

    Try it: GET http://localhost:5000/api/products
    """
    if os.getenv("USE_DATABRICKS", "false").lower() == "true":
        results = run_query("SELECT id, name, category, price FROM products")
        if isinstance(results, dict) and results.get("error"):
            return jsonify({"error": results["error"]}), 500
        return jsonify({
            "count": len(results),
            "products": results
        })

    db = get_db()
    products = db.query(Product).all()
    db.close()

    return jsonify({
        "count": len(products),
        "products": [p.to_dict() for p in products]
    })


# =============================================================================
# ROUTE 3: Get Sales Summary
# =============================================================================
@app.route('/api/sales/summary', methods=['GET'])
def get_sales_summary():
    """
    Returns a summary of sales data.

    Try it: GET http://localhost:5000/api/sales/summary
    """
    # Total sales
    total_result = run_query("SELECT SUM(total) as total, COUNT(*) as count FROM sales")
    if isinstance(total_result, dict) and total_result.get("error"):
        return jsonify({"error": total_result["error"]}), 500

    # Sales by region
    by_region = run_query("""
        SELECT region, SUM(total) as total, COUNT(*) as count
        FROM sales GROUP BY region ORDER BY total DESC
    """)
    if isinstance(by_region, dict) and by_region.get("error"):
        return jsonify({"error": by_region["error"]}), 500

    # Sales by category
    by_category = run_query("""
        SELECT p.category, SUM(s.total) as total, COUNT(*) as count
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.category ORDER BY total DESC
    """)
    if isinstance(by_category, dict) and by_category.get("error"):
        return jsonify({"error": by_category["error"]}), 500

    # Top products
    top_products = run_query("""
        SELECT p.name, SUM(s.total) as total, SUM(s.quantity) as units_sold
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.name ORDER BY total DESC LIMIT 5
    """)
    if isinstance(top_products, dict) and top_products.get("error"):
        return jsonify({"error": top_products["error"]}), 500

    return jsonify({
        "total_sales": total_result[0]['total'] if total_result else 0,
        "total_transactions": total_result[0]['count'] if total_result else 0,
        "by_region": by_region,
        "by_category": by_category,
        "top_products": top_products
    })


# =============================================================================
# ROUTE 4: Run SQL Query (for testing - will be used by AI agent)
# =============================================================================
@app.route('/api/query', methods=['POST'])
@require_auth
def execute_query():
    """
    Execute a SQL query and return results.
    ⚠️ In production, you'd add security here!

    Try it:
    curl -X POST http://localhost:5000/api/query \
         -H "Content-Type: application/json" \
         -d '{"sql": "SELECT * FROM products LIMIT 3"}'
    """
    data = request.json
    sql = data.get('sql', '')

    if not sql:
        return jsonify({"error": "No SQL query provided"}), 400

    # Basic safety check (the AI agent will have better validation)
    forbidden = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE']
    if any(word in sql.upper() for word in forbidden):
        return jsonify({"error": "Only SELECT queries allowed"}), 400

    results = run_query(sql)
    if isinstance(results, dict) and results.get("error"):
        return jsonify({"error": results["error"]}), 500

    return jsonify({
        "query": sql,
        "results": results,
        "row_count": len(results) if isinstance(results, list) else 0
    })


# =============================================================================
# ROUTE 5: Get Database Schema (AI agent needs this!)
# =============================================================================
@app.route('/api/schema', methods=['GET'])
def get_schema():
    """
    Returns the database schema information.
    The AI agent uses this to understand what data is available.

    Try it: GET http://localhost:5000/api/schema
    """
    return jsonify({
        "schema": get_schema_info(),
        "tables": ["products", "sales"],
        "tip": "The AI agent reads this to know what queries it can write!"
    })


# =============================================================================
# ROUTE 6: Ask Endpoint (MODULE 4: TEXT-TO-SQL AGENT!)
# =============================================================================
@app.route('/api/ask', methods=['POST'])
@require_auth
@rate_limit
def ask():
    """
    AI-powered question answering with Text-to-SQL capability!

    MODULE 4 IMPLEMENTATION:
    - Converts natural language to SQL queries
    - Executes queries against the database
    - Returns data-driven answers with actual results

    The agent workflow:
    1. Receives your question
    2. Generates SQL query using LangChain
    3. Validates the SQL for safety
    4. Executes the query
    5. Formats results into natural language

    Try it:
    curl -X POST http://localhost:5000/api/ask \
         -H "Content-Type: application/json" \
         -d '{"question": "What are the total sales?"}'

    More examples:
    - "How many products are in the Electronics category?"
    - "Show me the top 3 products by price"
    - "What are total sales by region?"
    - "What's the average sale amount?"
    """
    data = request.json
    question = data.get('question', '')
    session_id = data.get('session_id')
    use_module_3 = data.get('use_basic_mode', False)  # Option to use old Module 3 mode

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # MODULE 4: Use LangChain Text-to-SQL agent with user context
    if not use_module_3:
        result = text_to_sql_agent(
            question,
            return_sql=True,
            user_id=g.user_id,
            user_email=g.user_email
        )

        if result['success']:
            # Save to query history
            metrics = result.get('metrics', {})
            save_query_history(
                user_id=g.user_id,
                question=question,
                answer=result['answer'],
                sql_query=result.get('sql'),
                agent_type='text_to_sql',
                cache_hit=result.get('cache_hit', False),
                duration_seconds=metrics.get('total_duration_seconds'),
                session_id=session_id
            )

            return jsonify({
                "question": question,
                "answer": result['answer'],
                "sql": result.get('sql'),
                "results": result.get('results'),
                "row_count": result.get('row_count'),
                "success": True,
                "module": "Module 4: Text-to-SQL Agent",
                "agent_type": "LangChain SQL Agent",
                "cache_hit": result.get('cache_hit', False),
                "metrics": result.get('metrics')
            })
        else:
            return jsonify({
                "question": question,
                "error": result.get('error'),
                "success": False,
                "module": "Module 4: Text-to-SQL Agent"
            }), 500

    # MODULE 3: Fallback to basic OpenAI assistant (no database access)
    else:
        result = ai_sales_assistant(question)
        return jsonify({
            "question": question,
            "answer": result['answer'],
            "success": result['success'],
            "module": "Module 3: Basic OpenAI Integration",
            "note": "Not using database. Set 'use_basic_mode': false to use Text-to-SQL agent",
            "usage": result.get('usage', {})
        })


# =============================================================================
# ROUTE 7: Enhanced Agent Endpoint (MODULE 5: AGENT WITH TOOLS!)
# =============================================================================
@app.route('/api/agent', methods=['POST'])
@require_auth
@rate_limit
def agent_endpoint():
    """
    Enhanced AI agent with tools and multi-step reasoning!

    MODULE 5 FEATURES:
    - Multiple tools (QueryDatabase, GetSchema, Calculate, GetDate)
    - Multi-step reasoning capability
    - Better at complex questions

    Try it:
    curl -X POST http://localhost:5000/api/agent \
         -H "Content-Type: application/json" \
         -d '{"question": "What are the top 3 products and what is their average price?"}'
    """
    data = request.json
    question = data.get('question', '')
    session_id = data.get('session_id')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # MODULE 5: Use enhanced agent with tools and user context
    result = agent_with_tools(
        question,
        user_id=g.user_id,
        user_email=g.user_email
    )

    if result['success']:
        # Save to query history
        metrics = result.get('metrics', {})
        save_query_history(
            user_id=g.user_id,
            question=question,
            answer=result['answer'],
            sql_query=result.get('sql'),
            agent_type='tool_agent',
            cache_hit=result.get('cache_hit', False),
            duration_seconds=metrics.get('total_duration_seconds'),
            session_id=session_id
        )

        return jsonify({
            "question": question,
            "answer": result['answer'],
            "success": True,
            "module": "Module 5: Enhanced Agent with Tools",
            "agent_type": result.get('agent_type'),
            "tools_available": result.get('tools_available', []),
            "tools_used": result.get('tools_used', []),
            "sql": result.get('sql'),
            "results": result.get('results'),
            "cache_hit": result.get('cache_hit', False),
            "metrics": result.get('metrics')
        })
    else:
        return jsonify({
            "question": question,
            "error": result.get('error'),
            "success": False,
            "module": "Module 5: Enhanced Agent with Tools"
        }), 500


# =============================================================================
# ROUTE 8: Middleware Stats (for debugging/monitoring)
# =============================================================================
@app.route('/api/stats/cache', methods=['GET'])
@require_auth
def get_cache_stats():
    """
    Get cache statistics for monitoring.

    Returns cache hit rate, entry count, and eviction stats.
    """
    cache = get_response_cache()
    return jsonify(cache.get_stats())


@app.route('/api/stats/rate-limit', methods=['GET'])
@require_auth
def get_rate_limit_stats():
    """
    Get current user's rate limit status.

    Returns remaining requests per minute/hour.
    """
    limiter = get_rate_limiter()
    return jsonify(limiter.get_user_status(g.user_id))


# =============================================================================
# ROUTE 9: Query History
# =============================================================================
@app.route('/api/history', methods=['GET'])
@require_auth
def get_query_history():
    """
    Get the current user's query history.

    Query params:
    - limit: Max number of queries to return (default 50)

    Try it:
    curl -H "Authorization: Bearer <token>" http://localhost:5001/api/history
    """
    limit = request.args.get('limit', 50, type=int)
    history = get_user_query_history(g.user_id, limit=limit)
    return jsonify({
        "history": history,
        "count": len(history)
    })


# =============================================================================
# ROUTE 10: Chat Sessions
# =============================================================================
@app.route('/api/sessions', methods=['GET'])
@require_auth
def list_sessions():
    """
    Get all chat sessions for the current user.

    Try it:
    curl -H "Authorization: Bearer <token>" http://localhost:5001/api/sessions
    """
    sessions = get_user_sessions(g.user_id)
    return jsonify({
        "sessions": sessions,
        "count": len(sessions)
    })


@app.route('/api/sessions', methods=['POST'])
@require_auth
def create_session():
    """
    Create a new chat session.

    Try it:
    curl -X POST -H "Authorization: Bearer <token>" http://localhost:5001/api/sessions
    """
    session = create_chat_session(g.user_id)
    if session:
        return jsonify(session), 201
    return jsonify({"error": "Failed to create session"}), 500


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
@require_auth
def get_session(session_id):
    """
    Get a specific session with its messages.

    Try it:
    curl -H "Authorization: Bearer <token>" http://localhost:5001/api/sessions/1
    """
    session = get_session_by_id(session_id, g.user_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    messages = get_session_messages(session_id, g.user_id)
    return jsonify({
        "session": session,
        "messages": messages
    })


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
@require_auth
def update_session(session_id):
    """
    Update a session's title.

    Try it:
    curl -X PUT -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
         -d '{"title": "New Title"}' http://localhost:5001/api/sessions/1
    """
    data = request.json
    title = data.get('title')

    if not title:
        return jsonify({"error": "Title is required"}), 400

    session = update_session_title(session_id, g.user_id, title)
    if session:
        return jsonify(session)
    return jsonify({"error": "Session not found"}), 404


# =============================================================================
# Run the Server
# =============================================================================
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 AI Agent Backend - Full-Stack with Authentication")
    print("="*70)
    print("\n✨ All modules ready with JWT authentication!")
    print("\nAuth Endpoints (Public):")
    print("  POST /api/auth/register - Register new user")
    print("  POST /api/auth/login    - Login, get JWT tokens")
    print("  POST /api/auth/refresh  - Refresh access token")
    print("  GET  /api/auth/me       - Get current user (🔐 protected)")
    print("\nData Endpoints (Public):")
    print("  GET  /                  - Health check")
    print("  GET  /api/products      - List all products")
    print("  GET  /api/sales/summary - Sales dashboard data")
    print("  GET  /api/schema        - Database schema (for AI)")
    print("\nAgent Endpoints (🔐 Protected - require JWT + Rate Limited):")
    print("  POST /api/query         - Run SQL query")
    print("  POST /api/ask           - 🤖 TEXT-TO-SQL AGENT (Module 4)")
    print("  POST /api/agent         - 🧠 ENHANCED AGENT (Module 5)")
    print("\nMiddleware Stats (🔐 Protected):")
    print("  GET  /api/stats/cache      - Cache statistics")
    print("  GET  /api/stats/rate-limit - Rate limit status")
    print("\nExample authenticated request:")
    print('  curl -X POST http://localhost:5000/api/ask \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -H "Authorization: Bearer <your-token>" \\')
    print("       -d '{\"question\": \"What are the total sales?\"}'")
    print("\n" + "="*70 + "\n")

    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", debug=True, port=port)
