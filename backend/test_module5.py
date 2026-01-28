"""
Quick smoke tests for Module 5 (tool-equipped agent).
Run: python test_module5.py
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5000"
API_URL = f"{BASE_URL}/api/agent"
REGISTER_URL = f"{BASE_URL}/api/auth/register"
LOGIN_URL = f"{BASE_URL}/api/auth/login"

def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_user_and_token(email: str, password: str, name: str = "Test User") -> str:
    try:
        post_json(REGISTER_URL, {"email": email, "password": password, "name": name})
    except urllib.error.HTTPError as exc:
        if exc.code != 400:
            raise
    login_result = post_json(LOGIN_URL, {"email": email, "password": password})
    return login_result["access_token"]


def post_question(question: str, token: str) -> dict:
    return post_json(API_URL, {"question": question}, token=token)


def run_test(label: str, question: str, token: str, expect_tools: bool = True) -> None:
    print(f"\n=== {label} ===")
    print(f"Q: {question}")
    result = post_question(question, token)
    tools_used = result.get("tools_used", [])
    print(f"tools_used: {tools_used}")
    print(f"answer: {result.get('answer', '')}")
    if expect_tools and not tools_used:
        print("FAIL: expected tools_used to be non-empty")
    else:
        print("PASS")


if __name__ == "__main__":
    print("Module 5 smoke tests (make sure the Flask server is running).")
    email = "test@example.com"
    password = "password123"
    token = None
    tests = [
        ("Total sales", "What are the total sales?"),
        ("Top 3 + average", "What are the top 3 products and their average price?"),
        ("Schema question", "What tables and columns are available?"),
    ]

    try:
        token = ensure_user_and_token(email, password)
    except urllib.error.URLError as exc:
        print(f"ERROR: {exc}")
        print("Is the backend running at http://localhost:5000?")
        raise SystemExit(1)
    except urllib.error.HTTPError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    for label, question in tests:
        try:
            run_test(label, question, token)
        except urllib.error.URLError as exc:
            print(f"ERROR: {exc}")
            print("Is the backend running at http://localhost:5000?")
            break
