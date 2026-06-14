import json
import os
from utils.logger import log

MEMORY_FILE = "reports/agent_memory.json"

class Memory:
    def __init__(self):
        self.data = {
            "sessions": 0,
            "working_selectors": {},
            "page_patterns": {},
            "test_results_history": [],
            "learned_skills": [],
            "failures": [],
            "known_pages": []
        }
        self._load()

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    saved = json.load(f)
                    self.data.update(saved)
                log(f"Memory loaded: {self.data['sessions']} previous sessions")
            except Exception:
                log("Could not load memory, starting fresh", level="WARN")

    def save(self):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
        log("Memory saved")

    def increment_session(self):
        self.data["sessions"] += 1
        log(f"Session #{self.data['sessions']}")

    def remember_selector(self, field_name, selector):
        self.data["working_selectors"][field_name] = selector
        log(f"Remembered selector: {field_name} -> {selector}")

    def get_known_selector(self, field_name):
        return self.data["working_selectors"].get(field_name, None)

    def remember_page(self, page_name, page_data):
        for p in self.data["known_pages"]:
            if p["name"] == page_name:
                p.update(page_data)
                return
        self.data["known_pages"].append({"name": page_name, **page_data})

    def remember_test_result(self, test_id, test_name, status, details=""):
        result = {
            "test_id": test_id,
            "test_name": test_name,
            "status": status,
            "details": details,
            "session": self.data["sessions"]
        }
        self.data["test_results_history"].append(result)

    def remember_failure(self, test_name, reason, suggestion=""):
        self.data["failures"].append({
            "test": test_name,
            "reason": reason,
            "suggestion": suggestion,
            "session": self.data["sessions"]
        })

    def learn_skill(self, skill_name, steps):
        for s in self.data["learned_skills"]:
            if s["name"] == skill_name:
                s["steps"] = steps
                s["times_used"] = s.get("times_used", 0) + 1
                return
        self.data["learned_skills"].append({
            "name": skill_name,
            "steps": steps,
            "times_used": 1
        })
        log(f"Learned new skill: {skill_name}")

    def get_skill(self, skill_name):
        for s in self.data["learned_skills"]:
            if s["name"] == skill_name:
                return s
        return None

    def get_session_results(self):
        current = self.data["sessions"]
        return [r for r in self.data["test_results_history"] if r["session"] == current]

    def get_summary(self):
        current_results = self.get_session_results()
        passed = sum(1 for r in current_results if r["status"] == "PASS")
        failed = sum(1 for r in current_results if r["status"] == "FAIL")
        skipped = sum(1 for r in current_results if r["status"] == "SKIP")
        return {
            "session": self.data["sessions"],
            "total_tests": len(current_results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": f"{(passed / len(current_results) * 100):.1f}%" if current_results else "0%",
            "skills_learned": len(self.data["learned_skills"]),
            "known_selectors": len(self.data["working_selectors"])
        }

# import json
# import os
# from utils.logger import log

# MEMORY_FILE = "reports/agent_memory.json"

# class Memory:
#     def __init__(self):
#         self.data = {
#             "sessions": 0,
#             "working_selectors": {},
#             "page_patterns": {},
#             "test_results_history": [],
#             "learned_skills": [],
#             "failures": [],
#             "known_pages": []
#         }
#         self._load()

#     def _load(self):
#         if os.path.exists(MEMORY_FILE):
#             try:
#                 with open(MEMORY_FILE, "r") as f:
#                     saved = json.load(f)
#                     self.data.update(saved)
#                 log(f"Memory loaded: {self.data['sessions']} previous sessions")
#             except Exception:
#                 log("Could not load memory, starting fresh", level="WARN")

#     def save(self):
#         os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
#         with open(MEMORY_FILE, "w") as f:
#             json.dump(self.data, f, indent=2)
#         log("Memory saved")

#     def increment_session(self):
#         self.data["sessions"] += 1
#         log(f"Session #{self.data['sessions']}")

#     def remember_selector(self, field_name, selector):
#         self.data["working_selectors"][field_name] = selector
#         log(f"Remembered selector: {field_name} -> {selector}")

#     def get_known_selector(self, field_name):
#         return self.data["working_selectors"].get(field_name, None)

#     def remember_page(self, page_name, page_data):
#         for p in self.data["known_pages"]:
#             if p["name"] == page_name:
#                 p.update(page_data)
#                 return
#         self.data["known_pages"].append({"name": page_name, **page_data})

#     def remember_test_result(self, test_id, test_name, status, details=""):
#         result = {
#             "test_id": test_id,
#             "test_name": test_name,
#             "status": status,
#             "details": details,
#             "session": self.data["sessions"]
#         }
#         self.data["test_results_history"].append(result)

#     def remember_failure(self, test_name, reason, suggestion=""):
#         self.data["failures"].append({
#             "test": test_name,
#             "reason": reason,
#             "suggestion": suggestion,
#             "session": self.data["sessions"]
#         })

#     def learn_skill(self, skill_name, steps):
#         for s in self.data["learned_skills"]:
#             if s["name"] == skill_name:
#                 s["steps"] = steps
#                 s["times_used"] = s.get("times_used", 0) + 1
#                 return
#         self.data["learned_skills"].append({
#             "name": skill_name,
#             "steps": steps,
#             "times_used": 1
#         })
#         log(f"Learned new skill: {skill_name}")

#     def get_skill(self, skill_name):
#         for s in self.data["learned_skills"]:
#             if s["name"] == skill_name:
#                 return s
#         return None

#     def get_session_results(self):
#         current = self.data["sessions"]
#         return [r for r in self.data["test_results_history"] if r["session"] == current]

#     def get_summary(self):
#         current_results = self.get_session_results()
#         passed = sum(1 for r in current_results if r["status"] == "PASS")
#         failed = sum(1 for r in current_results if r["status"] == "FAIL")
#         skipped = sum(1 for r in current_results if r["status"] == "SKIP")
#         return {
#             "session": self.data["sessions"],
#             "total_tests": len(current_results),
#             "passed": passed,
#             "failed": failed,
#             "skipped": skipped,
#             "pass_rate": f"{(passed / len(current_results) * 100):.1f}%" if current_results else "0%",
#             "skills_learned": len(self.data["learned_skills"]),
#             "known_selectors": len(self.data["working_selectors"])
#         }