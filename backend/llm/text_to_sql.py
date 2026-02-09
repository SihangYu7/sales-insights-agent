"""
AI Agent Backend - Module 4: LangChain Text-to-SQL Agent
=========================================================
This module implements the core AI agent functionality: converting natural
language questions into SQL queries and executing them.

KEY CONCEPTS YOU'LL LEARN:
- LangChain: Framework for building LLM applications
- Text-to-SQL: Converting natural language to database queries
- Schema injection: Teaching the AI about database structure
- Query validation: Preventing dangerous SQL operations
- Chain of Thought: AI explains its reasoning

WHY THIS MATTERS:
This is where your AI agent becomes truly useful! Instead of just chatting,
it can now access real data and answer data-driven questions.

ARCHITECTURE:
User Question → Schema Context → LLM → SQL Query → Validation → Execution → Response
"""

import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.callbacks import BaseCallbackHandler

# Database imports
from analytics.query import get_schema_info, run_query
from config import get_openai_model

# Middleware imports
from middleware.callbacks import create_callback_handlers, MetricsCallbackHandler
from middleware.cache import get_cached_response, cache_response

load_dotenv()


# =============================================================================
# LEARNING POINT 1: Creating a LangChain-compatible database connection
# =============================================================================
def get_langchain_db():
    """
    Create a LangChain SQLDatabase object.

    LangChain's SQLDatabase wraps SQLAlchemy and provides:
    - Schema information formatted for LLMs
    - Safe query execution
    - Integration with LangChain chains

    Uses the database connector abstraction to support both SQLite and Databricks.

    Returns:
        SQLDatabase: LangChain database wrapper
    """
    from analytics.connector import get_database_connector

    connector = get_database_connector()
    db_uri = connector.get_langchain_uri()
    return SQLDatabase.from_uri(db_uri)


def get_schema_for_prompt() -> str:
    """Return schema text for the SQL prompt, handling Databricks gracefully."""
    from analytics.connector import get_database_connector

    connector = get_database_connector()
    if connector.get_db_type() == "databricks":
        try:
            db = SQLDatabase.from_uri(connector.get_langchain_uri())
            return db.get_table_info()
        except Exception as e:
            print(f"⚠️ LangChain SQLDatabase connection failed: {e}")
            print("Using Databricks connector schema info instead.")
            return connector.get_schema_info()

    db = SQLDatabase.from_uri(connector.get_langchain_uri())
    return db.get_table_info()


# =============================================================================
# LEARNING POINT 2: SQL Query Validation (Security!)
# =============================================================================
def is_safe_sql(sql_query: str) -> tuple[bool, str]:
    """
    Validate SQL query to prevent dangerous operations.

    SECURITY CONCEPT: SQL Injection Prevention
    ------------------------------------------
    Even though an AI generated the query, we still need to validate it!
    - Block destructive operations (DROP, DELETE, UPDATE, etc.)
    - Only allow SELECT queries
    - Prevent potential abuse

    Args:
        sql_query: The SQL query to validate

    Returns:
        tuple: (is_safe: bool, message: str)

    Example:
        >>> is_safe_sql("SELECT * FROM products")
        (True, "Query is safe")

        >>> is_safe_sql("DROP TABLE products")
        (False, "Dangerous operation detected: DROP")
    """
    sql_upper = sql_query.upper().strip()

    # List of forbidden SQL keywords
    dangerous_keywords = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'RENAME'
    ]

    # Check for dangerous operations
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False, f"Dangerous operation detected: {keyword}"

    # Ensure it's a SELECT query
    if not sql_upper.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"

    return True, "Query is safe"


# =============================================================================
# LEARNING POINT 3: Custom Prompt for Text-to-SQL
# =============================================================================
def create_sql_prompt():
    """
    Create a custom prompt template for SQL generation.

    PROMPT ENGINEERING CONCEPT:
    ---------------------------
    The quality of AI output depends heavily on the prompt!
    We need to:
    1. Explain what the AI should do
    2. Provide database schema context
    3. Give examples of good queries
    4. Set constraints (only SELECT, etc.)

    Returns:
        PromptTemplate: LangChain prompt template
    """
    template = """You are a SQL expert helping users query a sales database.

Database Schema:
{schema}

Rules for SQL Generation:
1. Generate ONLY SELECT queries (no INSERT, UPDATE, DELETE, DROP)
2. Use proper JOIN syntax when querying multiple tables
3. Include appropriate WHERE clauses for filtering
4. Use aggregate functions (SUM, COUNT, AVG) when needed
5. Add ORDER BY and LIMIT for "top N" questions
6. Return ONLY the SQL query, no explanation

Question: {question}

SQL Query:"""

    return PromptTemplate(
        input_variables=["schema", "question"],
        template=template
    )


# =============================================================================
# LEARNING POINT 4: Building the Text-to-SQL Chain
# =============================================================================
def create_text_to_sql_chain(callbacks: List[BaseCallbackHandler] = None):
    """
    Create a LangChain chain that converts text to SQL.

    CHAIN CONCEPT:
    --------------
    A "chain" in LangChain is a sequence of operations:
    1. Get database schema
    2. Format prompt with schema + question
    3. Call LLM to generate SQL
    4. Parse the SQL from the response

    This is more reliable than calling OpenAI directly because:
    - Schema is automatically injected
    - Output parsing is handled
    - Error handling is built-in

    Args:
        callbacks: Optional list of LangChain callback handlers for middleware

    Returns:
        Chain: LangChain runnable chain
    """
    # Initialize the LLM with optional callbacks
    llm = ChatOpenAI(
        model=get_openai_model(),
        temperature=0,  # 0 = deterministic (best for SQL generation)
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        callbacks=callbacks
    )

    # Get schema information for the prompt
    schema_info = get_schema_for_prompt()

    # Create the prompt
    prompt = create_sql_prompt()

    # Build the chain
    # This is LangChain's "LCEL" (LangChain Expression Language) syntax
    chain = (
        {
            "schema": lambda _: schema_info,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


# =============================================================================
# LEARNING POINT 5: Main Agent Function
# =============================================================================
def text_to_sql_agent(
    question: str,
    return_sql: bool = True,
    user_id: int = None,
    user_email: str = None,
    callbacks: List[BaseCallbackHandler] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Main function: Convert natural language question to SQL and execute it.

    AGENT WORKFLOW:
    ---------------
    1. Check cache for existing response
    2. Generate SQL query using LangChain with callbacks
    3. Validate SQL for safety
    4. Execute query against database
    5. Cache and return results

    Args:
        question: Natural language question (e.g., "What are total sales?")
        return_sql: Whether to include the generated SQL in the response
        user_id: User ID for context tracking and caching
        user_email: User email for logging
        callbacks: Optional list of callback handlers (uses defaults if None)
        use_cache: Whether to use response caching

    Returns:
        dict: Response containing results, SQL, and metadata

    Example:
        >>> result = text_to_sql_agent("What are total sales?", user_id=123)
        >>> print(result)
        {
            "success": True,
            "question": "What are total sales?",
            "sql": "SELECT SUM(total) FROM sales",
            "results": [{"SUM(total)": 156789.50}],
            "row_count": 1,
            "answer": "The total sales are $156,789.50"
        }
    """
    try:
        # Step 0: Check cache first
        if use_cache:
            cached = get_cached_response(
                question=question,
                user_id=user_id,
                agent_type="text_to_sql"
            )
            if cached:
                cached["cache_hit"] = True
                print(f"📦 Cache hit for question: {question[:50]}...")
                return cached

        # Initialize callbacks if not provided
        if callbacks is None:
            callbacks = create_callback_handlers(
                user_id=user_id,
                user_email=user_email
            )

        # Find metrics handler for later retrieval
        metrics_handler = next(
            (h for h in callbacks if isinstance(h, MetricsCallbackHandler)),
            None
        )

        # Step 1: Generate SQL query
        print(f"📝 Question: {question}")

        chain = create_text_to_sql_chain(callbacks=callbacks)
        sql_query = chain.invoke(question)

        # Clean up the SQL (remove markdown code blocks if present)
        sql_query = sql_query.strip()
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.replace("```", "").strip()

        print(f"🔍 Generated SQL: {sql_query}")

        # Step 2: Validate SQL
        is_safe, safety_message = is_safe_sql(sql_query)
        if not is_safe:
            return {
                "success": False,
                "question": question,
                "error": f"Query validation failed: {safety_message}",
                "sql": sql_query if return_sql else None
            }

        # Step 3: Execute SQL
        results = run_query(sql_query)
        if isinstance(results, dict) and results.get("error"):
            return {
                "success": False,
                "question": question,
                "error": results["error"],
                "sql": sql_query if return_sql else None
            }

        print(f"✅ Query executed successfully. Rows returned: {len(results)}")

        # Step 4: Format human-friendly answer
        answer = format_results_as_answer(question, results, sql_query)

        # Step 5: Build response
        response = {
            "success": True,
            "question": question,
            "results": results,
            "row_count": len(results),
            "answer": answer,
            "cache_hit": False
        }

        if return_sql:
            response["sql"] = sql_query

        # Add metrics if available
        if metrics_handler:
            response["metrics"] = metrics_handler.get_metrics()

        # Step 6: Cache successful response
        if use_cache:
            cache_response(
                question=question,
                value=response,
                user_id=user_id,
                agent_type="text_to_sql",
                ttl=300  # 5 minutes
            )

        return response

    except Exception as e:
        print(f"❌ Error in text_to_sql_agent: {str(e)}")
        return {
            "success": False,
            "question": question,
            "error": f"Agent error: {str(e)}"
        }


# =============================================================================
# LEARNING POINT 6: Formatting Results for Humans
# =============================================================================
def format_results_as_answer(question: str, results: List[Dict], sql: str) -> str:
    """
    Convert raw SQL results into a human-friendly answer.

    NATURAL LANGUAGE GENERATION:
    ----------------------------
    Raw SQL results are often hard to read:
    [{"SUM(total)": 156789.50}]

    We want to convert this to:
    "The total sales are $156,789.50"

    This function uses another LLM call to generate natural language.

    Args:
        question: Original question
        results: Raw SQL results (list of dicts)
        sql: The SQL query that was executed

    Returns:
        str: Human-friendly answer
    """
    try:
        # If results are missing or not a list, return a friendly message
        if not isinstance(results, list):
            return f"Query failed: {results}"

        if not results or len(results) == 0:
            return "No results found for your query."

        # For simple queries with one value, format directly
        if len(results) == 1 and len(results[0]) == 1:
            value = list(results[0].values())[0]
            if isinstance(value, (int, float)):
                return f"The answer is: {value:,.2f}"
            return f"The answer is: {value}"

        # For more complex results, use LLM to format
        llm = ChatOpenAI(
            model=get_openai_model(),
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        formatting_prompt = f"""Convert these SQL query results into a natural language answer.

Question: {question}
SQL Query: {sql}
Results: {results}

Provide a clear, concise answer in 1-3 sentences. Include specific numbers and details from the results."""

        answer = llm.invoke(formatting_prompt)
        return answer.content

    except Exception as e:
        # If formatting fails, return raw results
        return f"Query returned {len(results)} results: {results[:3]}{'...' if len(results) > 3 else ''}"


# =============================================================================
# TESTING: Try the agent with sample questions
# =============================================================================
def test_text_to_sql_agent():
    """
    Test the text-to-sql agent with various questions.

    RUN THIS FUNCTION TO TEST MODULE 4!

    This tests:
    - Simple aggregation queries
    - Filtering queries
    - Top-N queries
    - Join queries
    """
    print("\n" + "="*70)
    print("🧪 TESTING MODULE 4: Text-to-SQL Agent")
    print("="*70 + "\n")

    test_questions = [
        "What are the total sales?",
        "How many products are in the Electronics category?",
        "What are the top 3 products by price?",
        "Show me total sales by region",
        "What's the average sale amount?"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n--- Test {i}/{len(test_questions)} ---")
        result = text_to_sql_agent(question)

        if result["success"]:
            print(f"✅ SUCCESS")
            print(f"SQL: {result.get('sql', 'N/A')}")
            print(f"Answer: {result['answer']}")
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")

        print()

    print("="*70)
    print("🎉 Module 4 Testing Complete!")
    print("="*70 + "\n")


# =============================================================================
# Entry point for testing
# =============================================================================
if __name__ == "__main__":
    # Run tests if this file is executed directly
    test_text_to_sql_agent()
