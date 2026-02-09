"""
AI Agent Backend - Module 5: LangChain Tools
==============================================
This module defines custom tools that the AI agent can use.

KEY CONCEPTS:
- Tool definition using @tool decorator (LangChain v1 pattern)
- Tool-calling via llm.bind_tools
- ReAct-style loop for multi-step reasoning

ARCHITECTURE:
Agent receives question → LLM decides tool calls → Tools run →
Synthesizes answer from tool results
"""

import os
import ast
import operator
import json
from typing import Dict, Any, List
from datetime import datetime

# LangChain imports
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai import ChatOpenAI

# Database imports
from analytics.query import run_query, get_schema_info
from llm.text_to_sql import is_safe_sql
from config import get_openai_model

# Middleware imports
from middleware.callbacks import create_callback_handlers, MetricsCallbackHandler
from middleware.cache import get_cached_response, cache_response

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# TOOL DEFINITIONS (LangChain v1 @tool decorator pattern)
# =============================================================================

@tool
def query_database(query: str) -> str:
    """Execute a SQL SELECT query against the sales database.

    Use this tool to retrieve data from the database. Only SELECT queries are allowed.

    Args:
        query: A valid SQL SELECT query string

    Examples:
        - "SELECT SUM(total) FROM sales WHERE region = 'North'"
        - "SELECT name, price FROM products ORDER BY price DESC LIMIT 5"
        - "SELECT category, COUNT(*) FROM products GROUP BY category"
    """
    try:
        is_safe, message = is_safe_sql(query)
        if not is_safe:
            return f"Error: {message}. Only SELECT queries are allowed."

        results = run_query(query)

        if isinstance(results, dict) and results.get("error"):
            return f"Error executing query: {results['error']}"

        if not results:
            return "Query executed successfully but returned no results."

        result_text = f"Query returned {len(results)} rows:\n"
        for i, row in enumerate(results[:10]):
            result_text += f"Row {i+1}: {row}\n"

        if len(results) > 10:
            result_text += f"... and {len(results) - 10} more rows"

        return result_text

    except Exception as e:
        return f"Error executing query: {str(e)}"


@tool
def get_schema() -> str:
    """Get the database schema information including tables and columns.

    Use this tool before writing SQL queries to understand what data is available.
    Returns information about all tables, their columns, and relationships.
    """
    try:
        schema = get_schema_info()

        if isinstance(schema, str):
            return schema

        result = f"Database type: {schema.get('database_type', 'Unknown')}\n"
        result += f"Available tables: {', '.join(schema.get('tables', {}).keys())}\n\n"

        for table, info in schema.get('tables', {}).items():
            result += f"\n{table}:\n"
            result += f"  Columns: {', '.join(info['columns'])}\n"
            if 'relationships' in info:
                result += f"  Relationships: {info['relationships']}\n"

        return result

    except Exception as e:
        return f"Error retrieving schema: {str(e)}"


@tool
def calculate(expression: str) -> str:
    """Perform mathematical calculations.

    Use this tool for arithmetic operations on data, computing percentages, growth rates, etc.

    Args:
        expression: A mathematical expression (e.g., "2 + 2", "100 * 0.15", "(45000 - 32000) / 32000 * 100")

    Supported operations: +, -, *, /, ** (power)
    """
    try:
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_expr(node):
            # Handle ast.Constant (Python 3.8+) and legacy ast.Num
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Num):  # Deprecated but kept for compatibility
                return node.n
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](eval_expr(node.operand))
            else:
                raise ValueError(f"Unsupported expression: {node}")

        node = ast.parse(expression, mode='eval')
        result = eval_expr(node.body)
        return f"Result: {result}"

    except Exception as e:
        return f"Error in calculation: {str(e)}. Please provide a valid mathematical expression."


@tool
def get_current_date() -> str:
    """Get today's current date in YYYY-MM-DD format.

    Use this tool when you need to know the current date for time-based queries or calculations.
    """
    return datetime.now().strftime("%Y-%m-%d")


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
SYSTEM_PROMPT = """You are a helpful data assistant with access to a sales database.

Your job is to answer questions about products and sales data accurately.
Use the available tools to query the database and perform calculations.

Guidelines:
- Use get_schema first if you're unsure about table structure
- Use query_database to execute SQL SELECT queries
- Use calculate for arithmetic operations on results
- Use get_current_date when you need today's date

Always provide clear, accurate answers based on the data you retrieve."""


# =============================================================================
# AGENT CREATION (LangChain v1 tool-calling pattern)
# =============================================================================
def create_sales_agent(callbacks: List[BaseCallbackHandler] = None):
    """
    Create a tool-calling LLM with bound tools.

    Args:
        callbacks: Optional list of callback handlers for logging/metrics

    Returns:
        tuple: (llm_with_tools, tools)
    """
    llm = ChatOpenAI(
        model=get_openai_model(),
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        callbacks=callbacks
    )

    tools = [query_database, get_schema, calculate, get_current_date]
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools, tools


# =============================================================================
# MAIN AGENT FUNCTION
# =============================================================================
def agent_with_tools(
    question: str,
    conversation_history: List[Dict] = None,
    user_id: int = None,
    user_email: str = None,
    callbacks: List[BaseCallbackHandler] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Answer questions using the tool-equipped agent.

    This agent can:
    - Query the database
    - Look up schema information
    - Perform calculations
    - Remember conversation context

    Args:
        question: User's question
        conversation_history: Previous messages (optional)
        user_id: User ID for context tracking and caching
        user_email: User email for logging
        callbacks: Optional list of callback handlers (uses defaults if None)
        use_cache: Whether to use response caching

    Returns:
        dict: Response with answer, tools used, and metadata
    """
    try:
        # Check cache first
        if use_cache:
            cached = get_cached_response(
                question=question,
                user_id=user_id,
                agent_type="tool_agent"
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

        print(f"\n🤖 Agent received question: {question}")
        print("=" * 70)

        # Create the tool-calling LLM and base LLM for final response
        llm_with_tools, tools = create_sales_agent(callbacks=callbacks)
        base_llm = ChatOpenAI(
            model=get_openai_model(),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            callbacks=callbacks
        )

        tools_by_name = {tool.name: tool for tool in tools}

        # Convert conversation history to LangChain messages
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=question))

        # Execute the tool-calling loop
        tools_used = []
        sql_query = None
        results_preview = None

        final_answer = None

        for _ in range(5):
            response = llm_with_tools.invoke(messages)
            tool_calls = getattr(response, "tool_calls", None) or []

            if not tool_calls:
                messages.append(response)
                final_answer = response.content
                break

            messages.append(response)

            for call in tool_calls:
                name = call.get("name")
                raw_args = call.get("args")

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args or {}

                tool_obj = tools_by_name.get(name)
                if not tool_obj:
                    tool_result = f"Error: Unknown tool '{name}'."
                else:
                    try:
                        tool_result = tool_obj.invoke(
                            args,
                            config={"callbacks": callbacks} if callbacks else None
                        )
                    except Exception as exc:
                        tool_result = f"Error executing tool '{name}': {str(exc)}"

                tools_used.append(name)

                if name == "query_database":
                    if isinstance(args, dict):
                        sql_query = args.get("query") or args.get("sql") or sql_query
                    else:
                        sql_query = str(args)
                    results_preview = tool_result

                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=call.get("id"))
                )

        if final_answer is None:
            messages.append(SystemMessage(
                content="Provide a final answer using the tool outputs above. Do not call tools."
            ))
            final_response = base_llm.invoke(messages)
            final_answer = final_response.content

        print("=" * 70)
        print("✅ Agent finished!\n")

        # Build response
        response = {
            "success": True,
            "question": question,
            "answer": final_answer,
            "sql": sql_query,
            "results": results_preview,
            "tools_available": ["query_database", "get_schema", "calculate", "get_current_date"],
            "tools_used": tools_used,
            "agent_type": "Tool-Equipped Agent (Module 5)",
            "cache_hit": False
        }

        if metrics_handler:
            response["metrics"] = metrics_handler.get_metrics()

        # Cache successful response
        if use_cache:
            cache_response(
                question=question,
                value=response,
                user_id=user_id,
                agent_type="tool_agent",
                ttl=300  # 5 minutes
            )

        return response

    except Exception as e:
        print(f"❌ Agent error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "question": question,
            "error": f"Agent error: {str(e)}"
        }


# =============================================================================
# TESTING: Try the agent with complex questions
# =============================================================================
def test_agent_with_tools():
    """
    Test the enhanced agent with multi-step reasoning questions.

    These questions require:
    - Multiple tool uses
    - Reasoning about results
    - Calculations on data
    """
    print("\n" + "="*70)
    print("🧪 TESTING MODULE 5: Enhanced Agent with Tools")
    print("="*70 + "\n")

    test_questions = [
        "What tables are available in the database?",
        "What's the average price of products in the Electronics category?",
        "Compare total sales between North and South regions. Which is higher and by how much percentage?",
        "How many total transactions were there, and what was the average transaction value?"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_questions)}")
        print(f"{'='*70}")

        result = agent_with_tools(question)

        if result["success"]:
            print(f"\n✅ ANSWER: {result['answer']}\n")
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}\n")

    print("="*70)
    print("🎉 Module 5 Testing Complete!")
    print("="*70 + "\n")


# =============================================================================
# Entry point for testing
# =============================================================================
if __name__ == "__main__":
    test_agent_with_tools()
