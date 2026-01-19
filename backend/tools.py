"""
AI Agent Backend - Module 5: LangChain Tools
==============================================
This module defines custom tools that the AI agent can use.

KEY CONCEPTS YOU'LL LEARN:
- Tool definition in LangChain
- Function calling / Tool use
- Agent reasoning patterns
- Multi-step problem solving

WHY TOOLS MATTER:
Tools give the AI agent "actions" it can take to gather information or
perform computations. Instead of just generating text, it can:
- Query databases
- Perform calculations
- Retrieve schema information
- Execute custom functions

ARCHITECTURE:
Agent receives question → Analyzes what tools are needed → Uses tools →
Synthesizes answer from tool results
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# LangChain imports
from langchain_core.tools import Tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

# Database imports
from database import run_query, get_schema_info
from langchain_agent import is_safe_sql

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# LEARNING POINT 1: Tool Functions
# =============================================================================
# Tools in LangChain are just Python functions with:
# 1. Clear input/output types
# 2. A description telling the AI when to use them
# 3. Error handling

def query_database_tool(query: str) -> str:
    """
    Execute a SQL SELECT query against the database.

    This tool allows the agent to retrieve data from the sales database.
    It includes safety checks to prevent dangerous operations.

    Args:
        query: SQL SELECT query to execute

    Returns:
        str: Query results as formatted text, or error message

    Example:
        >>> query_database_tool("SELECT * FROM products LIMIT 3")
        "Found 3 results: [product data...]"
    """
    try:
        # Validate the SQL
        is_safe, message = is_safe_sql(query)
        if not is_safe:
            return f"Error: {message}. Only SELECT queries are allowed."

        # Execute query
        results = run_query(query)

        if not results:
            return "Query executed successfully but returned no results."

        # Format results for the AI
        result_text = f"Query returned {len(results)} rows:\n"
        for i, row in enumerate(results[:10]):  # Show max 10 rows
            result_text += f"Row {i+1}: {row}\n"

        if len(results) > 10:
            result_text += f"... and {len(results) - 10} more rows"

        return result_text

    except Exception as e:
        return f"Error executing query: {str(e)}"


def get_database_schema_tool(table_name: Optional[str] = None) -> str:
    """
    Get information about database schema (tables, columns, relationships).

    This tool helps the agent understand what data is available and how
    to structure SQL queries.

    Args:
        table_name: Optional - specific table to get info about

    Returns:
        str: Formatted schema information

    Example:
        >>> get_database_schema_tool()
        "Database has 2 tables: products, sales..."
    """
    try:
        schema = get_schema_info()

        if isinstance(schema, str):
            # Current implementation returns a formatted string; just return it.
            return schema

        if table_name and table_name in schema.get('tables', {}):
            table_info = schema['tables'][table_name]
            result = f"Table: {table_name}\n"
            result += f"Columns: {', '.join(table_info['columns'])}\n"
            result += f"Description: {table_info.get('description', 'N/A')}\n"
            result += f"Sample query: {table_info.get('sample_query', 'N/A')}"
            return result

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


def calculate_tool(expression: str) -> str:
    """
    Perform mathematical calculations.

    This tool allows the agent to do arithmetic when analyzing data.
    Useful for percentage calculations, growth rates, etc.

    Args:
        expression: Mathematical expression to evaluate (e.g., "100 * 1.15")

    Returns:
        str: Result of calculation or error message

    Example:
        >>> calculate_tool("(45000 - 32000) / 32000 * 100")
        "40.625"
    """
    try:
        # Security: Use ast.literal_eval for safe evaluation
        # Only allows literals, not arbitrary code execution
        import ast
        import operator

        # Define allowed operators
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_expr(node):
            if isinstance(node, ast.Num):
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


def get_current_date_tool(format_string: str = "%Y-%m-%d") -> str:
    """
    Get the current date.

    Useful when the agent needs to calculate date ranges or understand
    how recent the data is.

    Args:
        format_string: Date format (default: YYYY-MM-DD)

    Returns:
        str: Current date formatted as string

    Example:
        >>> get_current_date_tool()
        "2024-01-19"
    """
    try:
        return datetime.now().strftime(format_string)
    except Exception as e:
        return f"Error getting date: {str(e)}"


# =============================================================================
# LEARNING POINT 2: Creating LangChain Tool Objects
# =============================================================================
# Wrap functions in LangChain Tool objects with descriptions

# Tool 1: Database Query
database_query_tool = Tool(
    name="QueryDatabase",
    func=query_database_tool,
    description="""
    Use this tool to execute SQL SELECT queries against the sales database.

    Input: A valid SQL SELECT query as a string
    Output: Query results or error message

    When to use:
    - User asks for specific data (sales figures, product info, etc.)
    - You need to retrieve data to answer a question
    - You want to count, sum, or aggregate data

    Example queries:
    - "SELECT SUM(total) FROM sales WHERE region = 'North'"
    - "SELECT name, price FROM products ORDER BY price DESC LIMIT 5"
    - "SELECT category, COUNT(*) FROM products GROUP BY category"

    Important: Only SELECT queries are allowed. No INSERT, UPDATE, DELETE, DROP.
    """
)

# Tool 2: Schema Information
schema_tool = Tool(
    name="GetSchema",
    func=get_database_schema_tool,
    description="""
    Use this tool to learn about the database structure.

    Input: Optional table name (string), or empty for all tables
    Output: Information about tables, columns, and relationships

    When to use:
    - Before writing SQL queries (to know what columns exist)
    - User asks "what data do you have?"
    - You're unsure about table structure
    - You need to understand relationships between tables

    Example:
    - GetSchema() - Get info about all tables
    - GetSchema("products") - Get info about products table specifically
    """
)

# Tool 3: Calculator
calculator_tool = Tool(
    name="Calculate",
    func=calculate_tool,
    description="""
    Use this tool to perform mathematical calculations.

    Input: Mathematical expression as a string
    Output: Calculation result

    When to use:
    - User asks for percentages or ratios
    - You need to compute growth rates
    - Compare values numerically
    - Do arithmetic on query results

    Example expressions:
    - "(45000 - 32000) / 32000 * 100"  (percent change)
    - "156789 / 200"  (average)
    - "999.99 * 0.8"  (discount calculation)

    Supported operations: +, -, *, /, ** (power)
    """
)

# Tool 4: Current Date
date_tool = Tool(
    name="GetCurrentDate",
    func=get_current_date_tool,
    description="""
    Use this tool to get today's date.

    Input: Optional date format string (default: YYYY-MM-DD)
    Output: Current date as formatted string

    When to use:
    - User asks about "recent" or "current" data
    - You need to calculate date ranges
    - Understanding data recency

    Example:
    - GetCurrentDate() returns "2024-01-19"
    """
)


# =============================================================================
# LEARNING POINT 3: Agent Creation with Tools
# =============================================================================
def create_agent_with_tools(verbose: bool = True):
    """
    Create a LangChain agent with our custom tools.

    AGENT vs CHAIN:
    ---------------
    - Chain: Pre-defined sequence of operations (Module 4)
    - Agent: Dynamically decides which tools to use and in what order

    Agents use "ReAct" pattern:
    1. Reason about the problem
    2. Act by using a tool
    3. Observe the result
    4. Repeat until answer is found

    Args:
        verbose: If True, print agent's reasoning process

    Returns:
        Callable: LLM with bound tools
    """
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,  # Deterministic reasoning
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Define available tools
    tools = [
        database_query_tool,
        schema_tool,
        calculator_tool,
        date_tool
    ]

    # Bind tools to the LLM (newer LangChain pattern)
    # This allows the LLM to call tools directly
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools


# =============================================================================
# LEARNING POINT 4: Using the Agent
# =============================================================================
def agent_with_tools(question: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Main function: Answer questions using the tool-equipped agent.

    This agent can:
    - Query the database
    - Look up schema information
    - Perform calculations
    - Remember conversation context

    Args:
        question: User's question
        conversation_history: Previous messages (optional)

    Returns:
        dict: Response with answer, tools used, and metadata

    Example:
        >>> result = agent_with_tools("What's the average price of Electronics?")
        >>> print(result['answer'])
        "Let me check... [Agent queries DB] The average price is $558.32"
    """
    try:
        print(f"\n🤖 Agent received question: {question}")
        print("="*70)

        llm_with_tools = create_agent_with_tools(verbose=True)
        base_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        tools_by_name = {
            "QueryDatabase": query_database_tool,
            "GetSchema": get_database_schema_tool,
            "Calculate": calculate_tool,
            "GetCurrentDate": get_current_date_tool
        }

        system_prompt = (
            "You are a data assistant. Use tools to answer questions with facts.\n"
            "When calling QueryDatabase, pass ONLY a valid SQL SELECT query string.\n"
            "Use Calculate for math and GetSchema if you need table/column info.\n"
            "After tool calls, respond with a clear final answer."
        )

        messages = [SystemMessage(content=system_prompt)]
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=question))

        tools_used = []
        sql_query = None
        results_preview = None

        for _ in range(5):
            response = llm_with_tools.invoke(messages)
            tool_calls = getattr(response, "tool_calls", None) or []

            if not tool_calls:
                messages.append(response)
                print("="*70)
                print("✅ Agent finished!\n")
                return {
                    "success": True,
                    "question": question,
                    "answer": response.content,
                    "sql": sql_query,
                    "results": results_preview,
                    "tools_available": list(tools_by_name.keys()),
                    "tools_used": tools_used,
                    "agent_type": "Tool-Equipped Agent (Module 5)"
                }

            messages.append(response)

            for call in tool_calls:
                name = call.get("name")
                raw_args = call.get("args")

                if name not in tools_by_name:
                    tool_result = f"Error: Unknown tool '{name}'."
                else:
                    try:
                        if isinstance(raw_args, str):
                            args = json.loads(raw_args) if raw_args else {}
                        else:
                            args = raw_args or {}
                    except json.JSONDecodeError:
                        args = {"query": raw_args} if isinstance(raw_args, str) else {}

                    tool_fn = tools_by_name[name]
                    if name == "QueryDatabase":
                        query = args.get("query") or args.get("sql") or ""
                        if not query.strip().upper().startswith("SELECT"):
                            from langchain_agent import text_to_sql_agent
                            fallback = text_to_sql_agent(question, return_sql=True)
                            if fallback.get("success") and fallback.get("sql"):
                                query = fallback["sql"]
                        sql_query = query or sql_query
                        tool_result = tool_fn(query)
                        results_preview = tool_result
                    elif name == "Calculate":
                        tool_result = tool_fn(args.get("expression", ""))
                    elif name == "GetSchema":
                        tool_result = tool_fn(args.get("table_name"))
                    elif name == "GetCurrentDate":
                        tool_result = tool_fn(args.get("format_string", "%Y-%m-%d"))
                    else:
                        tool_result = tool_fn(args)

                tools_used.append(name)
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=call.get("id")))

        messages.append(SystemMessage(
            content="Provide a final answer using the tool outputs above. Do not call tools."
        ))
        final_response = base_llm.invoke(messages)
        return {
            "success": True,
            "question": question,
            "answer": final_response.content,
            "sql": sql_query,
            "results": results_preview,
            "tools_available": list(tools_by_name.keys()),
            "tools_used": tools_used,
            "agent_type": "Tool-Equipped Agent (Module 5)"
        }

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
