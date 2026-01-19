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

from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, seed_database, run_query, get_schema_info, get_db, Product, Sale
from openai_service import ai_sales_assistant
from langchain_agent import text_to_sql_agent
from tools import agent_with_tools  # Module 5 - Now enabled!

# Create the Flask application
app = Flask(__name__)
CORS(app)


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
            "Module 5: Enhanced Agent with Tools"
        ]
    })


# =============================================================================
# ROUTE 2: Get All Products
# =============================================================================
@app.route('/api/products', methods=['GET'])
def get_products():
    """
    Returns all products in the database.

    Try it: GET http://localhost:5000/api/products
    """
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

    # Sales by region
    by_region = run_query("""
        SELECT region, SUM(total) as total, COUNT(*) as count
        FROM sales GROUP BY region ORDER BY total DESC
    """)

    # Sales by category
    by_category = run_query("""
        SELECT p.category, SUM(s.total) as total, COUNT(*) as count
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.category ORDER BY total DESC
    """)

    # Top products
    top_products = run_query("""
        SELECT p.name, SUM(s.total) as total, SUM(s.quantity) as units_sold
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.name ORDER BY total DESC LIMIT 5
    """)

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
    use_module_3 = data.get('use_basic_mode', False)  # Option to use old Module 3 mode

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # MODULE 4: Use LangChain Text-to-SQL agent
    if not use_module_3:
        result = text_to_sql_agent(question, return_sql=True)

        if result['success']:
            return jsonify({
                "question": question,
                "answer": result['answer'],
                "sql": result.get('sql'),
                "results": result.get('results'),
                "row_count": result.get('row_count'),
                "success": True,
                "module": "Module 4: Text-to-SQL Agent",
                "agent_type": "LangChain SQL Agent"
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

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # MODULE 5: Use enhanced agent with tools
    result = agent_with_tools(question)

    if result['success']:
        return jsonify({
            "question": question,
            "answer": result['answer'],
            "success": True,
            "module": "Module 5: Enhanced Agent with Tools",
            "agent_type": result.get('agent_type'),
            "tools_available": result.get('tools_available', []),
            "tools_used": result.get('tools_used', []),
            "sql": result.get('sql'),
            "results": result.get('results')
        })
    else:
        return jsonify({
            "question": question,
            "error": result.get('error'),
            "success": False,
            "module": "Module 5: Enhanced Agent with Tools"
        }), 500


# =============================================================================
# Run the Server
# =============================================================================
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 AI Agent Backend - Modules 4 & 5: Complete AI Agent")
    print("="*70)
    print("\n✨ Both Module 4 (Text-to-SQL) and Module 5 (Enhanced Agent) ready!")
    print("\nEndpoints available:")
    print("  GET  /                  - Health check")
    print("  GET  /api/products      - List all products")
    print("  GET  /api/sales/summary - Sales dashboard data")
    print("  GET  /api/schema        - Database schema (for AI)")
    print("  POST /api/query         - Run SQL query")
    print("  POST /api/ask           - 🤖 TEXT-TO-SQL AGENT (Module 4)")
    print("  POST /api/agent         - 🧠 ENHANCED AGENT (Module 5)")
    print("\nModule 4 questions → /api/ask:")
    print("  • What are the total sales?")
    print("  • Show me the top 3 products by price")
    print("\nModule 5 questions → /api/agent:")
    print("  • What are the top 3 products and their average price?")
    print("  • Compare Electronics vs Furniture average prices")
    print("\n" + "="*70 + "\n")

    app.run(debug=True, port=5000)
