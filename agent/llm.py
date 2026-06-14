import requests
import json
from utils.logger import log
import config
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def ask_llm(prompt):
    try:
        url = f"{config.LLM_ENDPOINT}/openai/deployments/{config.LLM_MODEL}/chat/completions?api-version={config.LLM_API_VERSION}"

        headers = {
            "Content-Type": "application/json",
            "api-key": config.LLM_API_KEY
        }

        body = {
            "messages": [
                {"role": "system", "content": "You are a testing agent. Analyze test results concisely."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_completion_tokens": 800
        }

        response = requests.post(url, headers=headers, json=body, timeout=30, verify=False)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"LLM error: {response.status_code} - {response.text[:200]}"

    except Exception as e:
        return f"LLM error: {str(e)[:200]}"

def analyze_after_tests(test_results, memory_data):
    passed = [t for t in test_results if t["status"] == "PASS"]
    failed = [t for t in test_results if t["status"] == "FAIL"]

    failed_summary = ""
    for f in failed:
        failed_summary += f"- {f['name']}: {f['details']}\n"

    if not failed_summary:
        failed_summary = "None — all tests passed!"

    prompt = f"""Analyze these automated test results for a web application:

Total: {len(test_results)} tests
Passed: {len(passed)}
Failed: {len(failed)}
Sessions completed: {memory_data.get('sessions', 0)}
Skills in memory: {len(memory_data.get('learned_skills', []))}

Failed tests:
{failed_summary}

Provide:
1. Root cause analysis for each failure (1 line each)
2. Are these real app bugs or test issues? (1 line each)
3. Top 3 recommended actions for the dev team
4. Suggest 3 NEW test cases that should be added"""

    return ask_llm(prompt)