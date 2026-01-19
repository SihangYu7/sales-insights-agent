"""
Quick smoke tests for Module 5 (tool-equipped agent).
Run: python test_module5.py
"""

import json
import urllib.request
import urllib.error

API_URL = "http://localhost:5000/api/agent"

def post_question(question: str) -> dict:
    payload = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_test(label: str, question: str, expect_tools: bool = True) -> None:
    print(f"\n=== {label} ===")
    print(f"Q: {question}")
    result = post_question(question)
    tools_used = result.get("tools_used", [])
    print(f"tools_used: {tools_used}")
    print(f"answer: {result.get('answer', '')}")
    if expect_tools and not tools_used:
        print("FAIL: expected tools_used to be non-empty")
    else:
        print("PASS")


if __name__ == "__main__":
    print("Module 5 smoke tests (make sure the Flask server is running).")
    tests = [
        ("Total sales", "What are the total sales?"),
        ("Top 3 + average", "What are the top 3 products and their average price?"),
        ("Schema question", "What tables and columns are available?"),
    ]

    for label, question in tests:
        try:
            run_test(label, question)
        except urllib.error.URLError as exc:
            print(f"ERROR: {exc}")
            print("Is the backend running at http://localhost:5000?")
            break
