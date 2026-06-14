from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from urllib.parse import urlparse
import json
import os
import threading
from utils.browser import launch_browser, close_browser
from utils.logger import log
from agent.brain import Brain
import config

app = FastAPI(title="APA Testing Agent API", redirect_slashes=False)

agent_state = {
    "status": "idle",
    "progress": "",
    "results": None,
    "error": None
}


class TestRequest(BaseModel):
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


def run_agent(url=None, username=None, password=None):
    global agent_state
    agent_state["status"] = "running"
    agent_state["progress"] = "Starting agent..."
    agent_state["error"] = None
    agent_state["results"] = None

    try:
        page = launch_browser()
        agent_state["progress"] = "Browser launched, agent starting..."

        agent = Brain(page, url=url, username=username, password=password)
        summary = agent.run()

        agent_state["results"] = summary
        agent_state["status"] = "completed"
        agent_state["progress"] = "All tests completed"

        close_browser()

    except Exception as e:
        agent_state["status"] = "failed"
        agent_state["error"] = str(e)
        agent_state["progress"] = f"Agent failed: {str(e)[:200]}"
        try:
            close_browser()
        except Exception:
            pass


@app.get("/")
def home():
    return {
        "name": "APA Testing Agent",
        "version": "2.0",
        "description": "Hermes-inspired autonomous testing agent with LLM + dynamic website testing",
        "endpoints": {
            "/run-tests": "POST - Start test execution (accepts url, username, password)",
            "/status": "GET - Check agent status",
            "/status/detailed": "GET - Detailed status with progress",
            "/results": "GET - Get test results",
            "/results/summary": "GET - Get summary",
            "/results/details": "GET - Get detailed category breakdown",
            "/report": "GET - Download HTML report",
            "/memory": "GET - View agent memory",
            "/memory/details": "GET - View formatted memory",
            "/analyze": "GET - LLM analysis of results",
            "/dashboard": "GET - Full dashboard data",
            "/stop": "POST - Stop agent",
            "/reset": "POST - Reset agent state"
        }
    }


@app.post("/run-tests")
def run_tests(request: TestRequest, background_tasks: BackgroundTasks):
    if agent_state["status"] == "running":
        return JSONResponse(
            status_code=409,
            content={"message": "Agent is already running", "status": agent_state["status"]}
        )

    background_tasks.add_task(
        run_agent,
        url=request.url,
        username=request.username,
        password=request.password
    )

    target = request.url or config.APP_URL
    return {
        "message": f"Agent started testing: {target}",
        "status": "running",
        "check_status": "/status",
        "get_results": "/results"
    }


@app.get("/status")
def get_status():
    return {
        "status": agent_state["status"],
        "progress": agent_state["progress"],
        "error": agent_state["error"]
    }


@app.get("/status/detailed")
def get_detailed_status():
    memory_path = "reports/agent_memory.json"

    if agent_state["status"] == "running":
        return {
            "status": "running",
            "progress": agent_state["progress"],
            "message": "Tests are executing. Please wait..."
        }

    if agent_state["status"] == "completed":
        result = {
            "status": "completed",
            "progress": agent_state["progress"],
            "message": "All tests completed!"
        }

        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                memory = json.load(f)
            skills = memory.get("learned_skills", [])
            llm_skill = next((s for s in skills if s["name"] == "llm_analysis"), None)
            if llm_skill:
                result["llm_analysis"] = llm_skill.get("steps", {}).get("analysis", "No analysis available")

        return result

    return {
        "status": agent_state["status"],
        "progress": agent_state["progress"],
        "message": "No tests running"
    }


@app.get("/results")
def get_results():
    if agent_state["status"] == "running":
        return {"message": "Agent is still running", "status": "running"}

    if agent_state["status"] == "idle":
        return {"message": "No tests have been run yet", "status": "idle"}

    report_path = "reports/test_report.json"
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)
        return {
            "status": "completed",
            "summary": agent_state["results"],
            "full_report": report
        }

    return {
        "status": agent_state["status"],
        "summary": agent_state["results"],
        "error": agent_state["error"]
    }


@app.get("/results/summary")
def get_summary():
    if agent_state["results"]:
        return {
            "status": "completed",
            "summary": agent_state["results"]
        }
    return {"status": agent_state["status"], "message": "No results available"}


@app.get("/results/details")
def get_detailed_results():
    report_path = "reports/test_report.json"
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)

        results = report.get("all_results", [])
        categories = report.get("categories", {})

        cat_summary = []
        for cat, counts in categories.items():
            cat_summary.append({
                "category": cat,
                "pass": counts.get("pass", 0),
                "fail": counts.get("fail", 0),
                "skip": counts.get("skip", 0)
            })

        failed = [
            {"name": r["name"], "details": r["details"]}
            for r in results if r["status"] == "FAIL"
        ]

        return {
            "total": len(results),
            "categories": cat_summary,
            "failed_tests": failed,
            "report_link": "http://localhost:8000/report"
        }

    return {"total": 0, "categories": [], "failed_tests": [], "report_link": ""}


@app.get("/report")
def get_report():
    report_path = "reports/test_report.html"
    if os.path.exists(report_path):
        return FileResponse(
            report_path,
            media_type="text/html",
            filename="test_report.html"
        )
    return JSONResponse(
        status_code=404,
        content={"message": "Report not generated yet. Run /run-tests first."}
    )


@app.get("/memory")
def get_memory():
    memory_path = "reports/agent_memory.json"
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = json.load(f)
        return memory
    return {"message": "No memory file found"}


@app.get("/memory/details")
def get_memory_details():
    memory_path = "reports/agent_memory.json"
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = json.load(f)

        sessions = memory.get("sessions", 0)
        skills = memory.get("learned_skills", [])
        selectors = memory.get("working_selectors", {})
        pages = memory.get("known_pages", [])
        failures = memory.get("failures", [])

        skills_text = ""
        for s in skills[:10]:
            skills_text += f"- {s['name']} (used {s.get('times_used', 1)}x)\n"
        if not skills_text:
            skills_text = "- No skills learned yet\n"

        selectors_text = ""
        for field, sel in selectors.items():
            selectors_text += f"- {field}: {sel}\n"
        if not selectors_text:
            selectors_text = "- No selectors stored yet\n"

        pages_text = ""
        for p in pages:
            pages_text += f"- {p.get('name', 'unknown')}: {p.get('url', '')}\n"
        if not pages_text:
            pages_text = "- No pages discovered yet\n"

        failures_text = ""
        recent_failures = [f for f in failures if f.get("session", 0) == sessions]
        for f in recent_failures:
            failures_text += f"- {f.get('test', 'unknown')}: {f.get('reason', '')}\n"
        if not failures_text:
            failures_text = "- No failures in latest session\n"

        return {
            "sessions": sessions,
            "total_skills": len(skills),
            "total_selectors": len(selectors),
            "total_pages": len(pages),
            "total_failures": len(recent_failures),
            "skills_text": skills_text,
            "selectors_text": selectors_text,
            "pages_text": pages_text,
            "failures_text": failures_text
        }

    return {"sessions": 0, "total_skills": 0, "skills_text": "No memory found"}


@app.get("/screenshots")
def list_screenshots():
    screenshot_dir = "screenshots"
    if os.path.exists(screenshot_dir):
        files = os.listdir(screenshot_dir)
        return {
            "count": len(files),
            "files": files
        }
    return {"count": 0, "files": []}


@app.get("/screenshots/{filename}")
def get_screenshot(filename: str):
    path = f"screenshots/{filename}"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    return JSONResponse(status_code=404, content={"message": "Screenshot not found"})


@app.post("/run-tests-sync")
def run_tests_sync(request: TestRequest):
    global agent_state
    agent_state["status"] = "running"

    try:
        page = launch_browser()
        agent = Brain(page, url=request.url, username=request.username, password=request.password)
        summary = agent.run()
        close_browser()

        agent_state["status"] = "completed"
        agent_state["results"] = summary

        return {
            "status": "completed",
            "total_tests": summary.get("total_tests", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "pass_rate": summary.get("pass_rate", "0%"),
            "skills_learned": summary.get("skills_learned", 0)
        }

    except Exception as e:
        agent_state["status"] = "failed"
        try:
            close_browser()
        except Exception:
            pass
        return {
            "status": "failed",
            "error": str(e)[:300]
        }


@app.post("/stop")
def stop_agent():
    if agent_state["status"] == "running":
        agent_state["status"] = "stopped"
        agent_state["progress"] = "Agent stopped by user"
        return {"message": "Stop signal sent"}
    return {"message": f"Agent is not running (status: {agent_state['status']})"}


@app.post("/reset")
def reset_agent():
    agent_state["status"] = "idle"
    agent_state["progress"] = ""
    agent_state["results"] = None
    agent_state["error"] = None
    return {"message": "Agent state reset"}


@app.get("/analyze")
def get_analysis():
    try:
        from agent.llm import analyze_after_tests

        report_path = "reports/test_report.json"
        memory_path = "reports/agent_memory.json"

        if not os.path.exists(report_path):
            return {"analysis": "No test results found. Run tests first."}

        with open(report_path, "r") as f:
            report = json.load(f)

        memory_data = {}
        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                memory_data = json.load(f)

        results = report.get("all_results", [])
        analysis = analyze_after_tests(results, memory_data)

        return {"analysis": analysis}

    except Exception as e:
        return {"analysis": f"Analysis failed: {str(e)[:200]}"}


@app.get("/dashboard")
def get_full_dashboard():
    report_path = "reports/test_report.json"
    memory_path = "reports/agent_memory.json"

    dashboard = {
        "status": agent_state["status"],
        "total": 0,
        "passed": 0,
        "failed": 0,
        "pass_rate": "0%",
        "sessions": 0,
        "skills": 0,
        "selectors": 0,
        "pages": 0,
        "llm_analysis": "No analysis available"
    }

    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)
        results = report.get("all_results", [])
        dashboard["total"] = len(results)
        dashboard["passed"] = len([r for r in results if r["status"] == "PASS"])
        dashboard["failed"] = len([r for r in results if r["status"] == "FAIL"])
        dashboard["pass_rate"] = report.get("summary", {}).get("pass_rate", "0%")

    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = json.load(f)
        dashboard["sessions"] = memory.get("sessions", 0)
        dashboard["skills"] = len(memory.get("learned_skills", []))
        dashboard["selectors"] = len(memory.get("working_selectors", {}))
        dashboard["pages"] = len(memory.get("known_pages", []))

        for skill in memory.get("learned_skills", []):
            if skill["name"] == "llm_analysis":
                dashboard["llm_analysis"] = skill.get("steps", {}).get("analysis", "No analysis available")

    return dashboard









# from fastapi import FastAPI, BackgroundTasks
# from fastapi.responses import FileResponse, JSONResponse
# import json
# import os
# import threading
# from utils.browser import launch_browser, close_browser
# from utils.logger import log
# from agent.brain import Brain

# # app = FastAPI(title="APA Testing Agent API")
# app = FastAPI(title="APA Testing Agent API", redirect_slashes=False)

# # Agent state
# agent_state = {
#     "status": "idle",
#     "progress": "",
#     "results": None,
#     "error": None
# }


# def run_agent():
#     global agent_state
#     agent_state["status"] = "running"
#     agent_state["progress"] = "Starting agent..."
#     agent_state["error"] = None
#     agent_state["results"] = None

#     try:
#         page = launch_browser()
#         agent_state["progress"] = "Browser launched, agent starting..."

#         agent = Brain(page)
#         summary = agent.run()

#         agent_state["results"] = summary
#         agent_state["status"] = "completed"
#         agent_state["progress"] = "All tests completed"

#         close_browser()

#     except Exception as e:
#         agent_state["status"] = "failed"
#         agent_state["error"] = str(e)
#         agent_state["progress"] = f"Agent failed: {str(e)[:200]}"
#         try:
#             close_browser()
#         except Exception:
#             pass


# @app.get("/")
# def home():
#     return {
#         "name": "APA Testing Agent",
#         "version": "1.0",
#         "description": "Hermes-inspired autonomous testing agent",
#         "endpoints": {
#             "/run-tests": "POST - Start test execution",
#             "/status": "GET - Check agent status",
#             "/results": "GET - Get test results",
#             "/results/summary": "GET - Get summary",
#             "/results/details": "GET - Get detailed category breakdown",
#             "/report": "GET - Download HTML report",
#             "/memory": "GET - View agent memory",
#             "/stop": "POST - Stop agent"
#         }
#     }


# @app.post("/run-tests")
# def run_tests(background_tasks: BackgroundTasks):
#     if agent_state["status"] == "running":
#         return JSONResponse(
#             status_code=409,
#             content={"message": "Agent is already running", "status": agent_state["status"]}
#         )

#     background_tasks.add_task(run_agent)

#     return {
#         "message": "Agent started",
#         "status": "running",
#         "check_status": "/status",
#         "get_results": "/results"
#     }


# @app.get("/status")
# def get_status():
#     return {
#         "status": agent_state["status"],
#         "progress": agent_state["progress"],
#         "error": agent_state["error"]
#     }


# @app.get("/results")
# def get_results():
#     if agent_state["status"] == "running":
#         return {"message": "Agent is still running", "status": "running"}

#     if agent_state["status"] == "idle":
#         return {"message": "No tests have been run yet", "status": "idle"}

#     report_path = "reports/test_report.json"
#     if os.path.exists(report_path):
#         with open(report_path, "r") as f:
#             report = json.load(f)
#         return {
#             "status": "completed",
#             "summary": agent_state["results"],
#             "full_report": report
#         }

#     return {
#         "status": agent_state["status"],
#         "summary": agent_state["results"],
#         "error": agent_state["error"]
#     }


# @app.get("/results/summary")
# def get_summary():
#     if agent_state["results"]:
#         return {
#             "status": "completed",
#             "summary": agent_state["results"]
#         }
#     return {"status": agent_state["status"], "message": "No results available"}


# @app.get("/results/details")
# def get_detailed_results():
#     report_path = "reports/test_report.json"
#     if os.path.exists(report_path):
#         with open(report_path, "r") as f:
#             report = json.load(f)

#         results = report.get("all_results", [])
#         categories = report.get("categories", {})

#         cat_summary = []
#         for cat, counts in categories.items():
#             cat_summary.append({
#                 "category": cat,
#                 "pass": counts.get("pass", 0),
#                 "fail": counts.get("fail", 0),
#                 "skip": counts.get("skip", 0)
#             })

#         failed = [
#             {"name": r["name"], "details": r["details"]}
#             for r in results if r["status"] == "FAIL"
#         ]

#         return {
#             "total": len(results),
#             "categories": cat_summary,
#             "failed_tests": failed,
#             "report_link": "http://localhost:8000/report"
#         }

#     return {"total": 0, "categories": [], "failed_tests": [], "report_link": ""}


# @app.get("/report")
# def get_report():
#     report_path = "reports/test_report.html"
#     if os.path.exists(report_path):
#         return FileResponse(
#             report_path,
#             media_type="text/html",
#             filename="test_report.html"
#         )
#     return JSONResponse(
#         status_code=404,
#         content={"message": "Report not generated yet. Run /run-tests first."}
#     )


# @app.get("/memory")
# def get_memory():
#     memory_path = "reports/agent_memory.json"
#     if os.path.exists(memory_path):
#         with open(memory_path, "r") as f:
#             memory = json.load(f)
#         return memory
#     return {"message": "No memory file found"}


# @app.get("/screenshots")
# def list_screenshots():
#     screenshot_dir = "screenshots"
#     if os.path.exists(screenshot_dir):
#         files = os.listdir(screenshot_dir)
#         return {
#             "count": len(files),
#             "files": files
#         }
#     return {"count": 0, "files": []}


# @app.get("/screenshots/{filename}")
# def get_screenshot(filename: str):
#     path = f"screenshots/{filename}"
#     if os.path.exists(path):
#         return FileResponse(path, media_type="image/png")
#     return JSONResponse(status_code=404, content={"message": "Screenshot not found"})


# @app.post("/stop")
# def stop_agent():
#     if agent_state["status"] == "running":
#         agent_state["status"] = "stopped"
#         agent_state["progress"] = "Agent stopped by user"
#         return {"message": "Stop signal sent"}
#     return {"message": f"Agent is not running (status: {agent_state['status']})"}


# @app.post("/reset")
# def reset_agent():
#     agent_state["status"] = "idle"
#     agent_state["progress"] = ""
#     agent_state["results"] = None
#     agent_state["error"] = None
#     return {"message": "Agent state reset"}


# @app.post("/run-tests-sync")
# def run_tests_sync():
#     global agent_state
#     agent_state["status"] = "running"

#     try:
#         page = launch_browser()
#         agent = Brain(page)
#         summary = agent.run()
#         close_browser()

#         agent_state["status"] = "completed"
#         agent_state["results"] = summary

#         return {
#             "status": "completed",
#             "total_tests": summary.get("total_tests", 0),
#             "passed": summary.get("passed", 0),
#             "failed": summary.get("failed", 0),
#             "skipped": summary.get("skipped", 0),
#             "pass_rate": summary.get("pass_rate", "0%"),
#             "skills_learned": summary.get("skills_learned", 0),
#             "report_url": "http://localhost:8000/report"
#         }

#     except Exception as e:
#         agent_state["status"] = "failed"
#         try:
#             close_browser()
#         except Exception:
#             pass
#         return {
#             "status": "failed",
#             "error": str(e)[:300]
#         }

# @app.get("/memory/details")
# def get_memory_details():
#     memory_path = "reports/agent_memory.json"
#     if os.path.exists(memory_path):
#         with open(memory_path, "r") as f:
#             memory = json.load(f)

#         sessions = memory.get("sessions", 0)
#         skills = memory.get("learned_skills", [])
#         selectors = memory.get("working_selectors", {})
#         pages = memory.get("known_pages", [])
#         failures = memory.get("failures", [])

#         # Build skills list
#         skills_text = ""
#         for s in skills[:10]:
#             skills_text += f"- {s['name']} (used {s.get('times_used', 1)}x)\n"
#         if not skills_text:
#             skills_text = "- No skills learned yet\n"

#         # Build selectors list
#         selectors_text = ""
#         for field, sel in selectors.items():
#             selectors_text += f"- {field}: {sel}\n"
#         if not selectors_text:
#             selectors_text = "- No selectors stored yet\n"

#         # Build known pages
#         pages_text = ""
#         for p in pages:
#             pages_text += f"- {p.get('name', 'unknown')}: {p.get('url', '')}\n"
#         if not pages_text:
#             pages_text = "- No pages discovered yet\n"

#         # Build failures
#         failures_text = ""
#         recent_failures = [f for f in failures if f.get("session", 0) == sessions]
#         for f in recent_failures:
#             failures_text += f"- {f.get('test', 'unknown')}: {f.get('reason', '')}\n"
#         if not failures_text:
#             failures_text = "- No failures in latest session\n"

#         return {
#             "sessions": sessions,
#             "total_skills": len(skills),
#             "total_selectors": len(selectors),
#             "total_pages": len(pages),
#             "total_failures": len(recent_failures),
#             "skills_text": skills_text,
#             "selectors_text": selectors_text,
#             "pages_text": pages_text,
#             "failures_text": failures_text
#         }

#     return {"sessions": 0, "total_skills": 0, "skills_text": "No memory found"}


# @app.get("/analyze")
# def get_analysis():
#     try:
#         from agent.llm import analyze_after_tests

#         report_path = "reports/test_report.json"
#         memory_path = "reports/agent_memory.json"

#         if not os.path.exists(report_path):
#             return {"analysis": "No test results found. Run tests first."}

#         with open(report_path, "r") as f:
#             report = json.load(f)

#         memory_data = {}
#         if os.path.exists(memory_path):
#             with open(memory_path, "r") as f:
#                 memory_data = json.load(f)

#         results = report.get("all_results", [])
#         analysis = analyze_after_tests(results, memory_data)

#         return {"analysis": analysis}

#     except Exception as e:
#         return {"analysis": f"Analysis failed: {str(e)[:200]}"}
    
# @app.get("/status/detailed")
# def get_detailed_status():
#     """Real-time status with progress percentage"""
#     report_path = "reports/test_report.json"
#     memory_path = "reports/agent_memory.json"

#     if agent_state["status"] == "running":
#         return {
#             "status": "running",
#             "progress": agent_state["progress"],
#             "message": "Tests are executing. Please wait..."
#         }

#     if agent_state["status"] == "completed":
#         result = {
#             "status": "completed",
#             "summary": agent_state["results"],
#             "message": "All tests completed!"
#         }

#         # Add LLM analysis if available
#         if os.path.exists(memory_path):
#             with open(memory_path, "r") as f:
#                 memory = json.load(f)
#             skills = memory.get("learned_skills", [])
#             llm_skill = next((s for s in skills if s["name"] == "llm_analysis"), None)
#             if llm_skill:
#                 result["llm_analysis"] = llm_skill.get("steps", {}).get("analysis", "No analysis available")

#         return result

#     return {
#         "status": agent_state["status"],
#         "progress": agent_state["progress"],
#         "message": "No tests running"
#     }


# @app.get("/analyze")
# def get_analysis():
#     """LLM analysis of latest test results"""
#     try:
#         from agent.llm import analyze_after_tests

#         report_path = "reports/test_report.json"
#         memory_path = "reports/agent_memory.json"

#         if not os.path.exists(report_path):
#             return {"analysis": "No test results found. Run tests first."}

#         with open(report_path, "r") as f:
#             report = json.load(f)

#         memory_data = {}
#         if os.path.exists(memory_path):
#             with open(memory_path, "r") as f:
#                 memory_data = json.load(f)

#         results = report.get("all_results", [])
#         analysis = analyze_after_tests(results, memory_data)

#         return {"analysis": analysis}

#     except Exception as e:
#         return {"analysis": f"Analysis failed: {str(e)[:200]}"}


# @app.get("/dashboard")
# def get_full_dashboard():
#     """Complete dashboard data for Copilot Studio"""
#     report_path = "reports/test_report.json"
#     memory_path = "reports/agent_memory.json"

#     dashboard = {
#         "status": agent_state["status"],
#         "summary": {},
#         "categories": {},
#         "memory": {},
#         "llm_analysis": "",
#         "failed_details": [],
#         "session_history": []
#     }

#     if os.path.exists(report_path):
#         with open(report_path, "r") as f:
#             report = json.load(f)

#         dashboard["summary"] = {
#             "total_tests": len(report.get("all_results", [])),
#             "passed": len([r for r in report.get("all_results", []) if r["status"] == "PASS"]),
#             "failed": len([r for r in report.get("all_results", []) if r["status"] == "FAIL"]),
#             "pass_rate": report.get("summary", {}).get("pass_rate", "0%")
#         }

#         dashboard["failed_details"] = [
#             {"name": r["name"], "details": r["details"], "category": r["category"]}
#             for r in report.get("all_results", []) if r["status"] == "FAIL"
#         ]

#         dashboard["categories"] = report.get("categories", {})

#     if os.path.exists(memory_path):
#         with open(memory_path, "r") as f:
#             memory = json.load(f)

#         dashboard["memory"] = {
#             "sessions": memory.get("sessions", 0),
#             "total_skills": len(memory.get("learned_skills", [])),
#             "known_selectors": len(memory.get("working_selectors", {})),
#             "known_pages": len(memory.get("known_pages", []))
#         }

#         # Get LLM analysis from memory
#         skills = memory.get("learned_skills", [])
#         llm_skill = next((s for s in skills if s["name"] == "llm_analysis"), None)
#         if llm_skill:
#             dashboard["llm_analysis"] = llm_skill.get("steps", {}).get("analysis", "")

#     return dashboard    





# from fastapi import FastAPI, BackgroundTasks
# from fastapi.responses import FileResponse, JSONResponse
# import json
# import os
# import threading
# from utils.browser import launch_browser, close_browser
# from utils.logger import log
# from agent.brain import Brain

# app = FastAPI(title="APA Testing Agent API")

# # Agent state
# agent_state = {
#     "status": "idle",
#     "progress": "",
#     "results": None,
#     "error": None
# }


# def run_agent():
#     global agent_state
#     agent_state["status"] = "running"
#     agent_state["progress"] = "Starting agent..."
#     agent_state["error"] = None
#     agent_state["results"] = None

#     try:
#         page = launch_browser()
#         agent_state["progress"] = "Browser launched, agent starting..."

#         agent = Brain(page)
#         summary = agent.run()

#         agent_state["results"] = summary
#         agent_state["status"] = "completed"
#         agent_state["progress"] = "All tests completed"

#         close_browser()

#     except Exception as e:
#         agent_state["status"] = "failed"
#         agent_state["error"] = str(e)
#         agent_state["progress"] = f"Agent failed: {str(e)[:200]}"
#         try:
#             close_browser()
#         except Exception:
#             pass


# @app.get("/")
# def home():
#     return {
#         "name": "APA Testing Agent",
#         "version": "1.0",
#         "description": "Hermes-inspired autonomous testing agent",
#         "endpoints": {
#             "/run-tests": "POST - Start test execution",
#             "/status": "GET - Check agent status",
#             "/results": "GET - Get test results",
#             "/report": "GET - Download HTML report",
#             "/memory": "GET - View agent memory",
#             "/stop": "POST - Stop agent"
#         }
#     }


# @app.post("/run-tests")
# def run_tests(background_tasks: BackgroundTasks):
#     if agent_state["status"] == "running":
#         return JSONResponse(
#             status_code=409,
#             content={"message": "Agent is already running", "status": agent_state["status"]}
#         )

#     background_tasks.add_task(run_agent)

#     return {
#         "message": "Agent started",
#         "status": "running",
#         "check_status": "/status",
#         "get_results": "/results"
#     }


# @app.get("/status")
# def get_status():
#     return {
#         "status": agent_state["status"],
#         "progress": agent_state["progress"],
#         "error": agent_state["error"]
#     }


# @app.get("/results")
# def get_results():
#     if agent_state["status"] == "running":
#         return {"message": "Agent is still running", "status": "running"}

#     if agent_state["status"] == "idle":
#         return {"message": "No tests have been run yet", "status": "idle"}

#     # Load from saved report
#     report_path = "reports/test_report.json"
#     if os.path.exists(report_path):
#         with open(report_path, "r") as f:
#             report = json.load(f)
#         return {
#             "status": "completed",
#             "summary": agent_state["results"],
#             "full_report": report
#         }

#     return {
#         "status": agent_state["status"],
#         "summary": agent_state["results"],
#         "error": agent_state["error"]
#     }


# @app.get("/results/summary")
# def get_summary():
#     if agent_state["results"]:
#         return {
#             "status": "completed",
#             "summary": agent_state["results"]
#         }
#     return {"status": agent_state["status"], "message": "No results available"}


# @app.get("/report")
# def get_report():
#     report_path = "reports/test_report.html"
#     if os.path.exists(report_path):
#         return FileResponse(
#             report_path,
#             media_type="text/html",
#             filename="test_report.html"
#         )
#     return JSONResponse(
#         status_code=404,
#         content={"message": "Report not generated yet. Run /run-tests first."}
#     )


# @app.get("/memory")
# def get_memory():
#     memory_path = "reports/agent_memory.json"
#     if os.path.exists(memory_path):
#         with open(memory_path, "r") as f:
#             memory = json.load(f)
#         return memory
#     return {"message": "No memory file found"}


# @app.get("/screenshots")
# def list_screenshots():
#     screenshot_dir = "screenshots"
#     if os.path.exists(screenshot_dir):
#         files = os.listdir(screenshot_dir)
#         return {
#             "count": len(files),
#             "files": files
#         }
#     return {"count": 0, "files": []}


# @app.get("/screenshots/{filename}")
# def get_screenshot(filename: str):
#     path = f"screenshots/{filename}"
#     if os.path.exists(path):
#         return FileResponse(path, media_type="image/png")
#     return JSONResponse(status_code=404, content={"message": "Screenshot not found"})


# @app.post("/stop")
# def stop_agent():
#     if agent_state["status"] == "running":
#         agent_state["status"] = "stopped"
#         agent_state["progress"] = "Agent stopped by user"
#         return {"message": "Stop signal sent"}
#     return {"message": f"Agent is not running (status: {agent_state['status']})"}


# @app.post("/reset")
# def reset_agent():
#     agent_state["status"] = "idle"
#     agent_state["progress"] = ""
#     agent_state["results"] = None
#     agent_state["error"] = None
#     return {"message": "Agent state reset"}

# @app.post("/run-tests-sync")
# def run_tests_sync():
#     """
#     Runs agent and waits for completion.
#     Returns results directly — perfect for Copilot Studio.
#     """
#     global agent_state
#     agent_state["status"] = "running"

#     try:
#         page = launch_browser()
#         agent = Brain(page)
#         summary = agent.run()
#         close_browser()

#         agent_state["status"] = "completed"
#         agent_state["results"] = summary

#         return {
#             "status": "completed",
#             "total_tests": summary.get("total_tests", 0),
#             "passed": summary.get("passed", 0),
#             "failed": summary.get("failed", 0),
#             "skipped": summary.get("skipped", 0),
#             "pass_rate": summary.get("pass_rate", "0%"),
#             "skills_learned": summary.get("skills_learned", 0),
#             "report_url": "http://localhost:8000/report"
#         }

#     except Exception as e:
#         agent_state["status"] = "failed"
#         try:
#             close_browser()
#         except Exception:
#             pass
#         return {
#             "status": "failed",
#             "error": str(e)[:300]
#         }