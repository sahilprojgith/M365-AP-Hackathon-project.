import json
import os
from utils.logger import log
from agent.executor import Executor
from agent.validator import Validator
from agent.planner import Planner
from agent.memory import Memory
from agent.reporter import Reporter
import config


class Brain:
    """
    The Agent Brain — Hermes-inspired autonomous testing agent.
    PERCEIVE -> PLAN -> ACT -> OBSERVE -> REMEMBER -> ADAPT -> REPORT
    Now with REAL learning across sessions.
    """

    def __init__(self, page, url=None, username=None, password=None):
        self.page = page
        self.executor = Executor(page, url=url, username=username, password=password)
        self.validator = Validator(page)
        self.planner = Planner(page, url=url)
        self.memory = Memory()
        self.test_results = []
        self.app_url = url or config.APP_URL

    def run(self):
        log("*" * 60)
        log("*    HERMES-INSPIRED APA TESTING AGENT    *")
        log("*" * 60)

        self.memory.increment_session()
        session = self.memory.data["sessions"]

        if session > 1:
            log(f"\n>>> AGENT MEMORY RECALL (Session #{session}) <<<")
            self._recall_memory()

        log("\n>>> AGENT PHASE: PERCEIVE <<<")
        login_ok = self._perceive()
        if not login_ok:
            log("Agent cannot proceed without login", level="ERROR")
            return self._finalize()

        log("\n>>> AGENT PHASE: PLAN <<<")
        tests = self._plan()
        if not tests:
            log("Agent has no tests to run", level="WARN")
            return self._finalize()

        log("\n>>> AGENT PHASE: ACT + OBSERVE + REMEMBER <<<")
        self._execute_all_tests(tests)

        log("\n>>> AGENT PHASE: ADAPT <<<")
        self._adapt()

        log("\n>>> AGENT PHASE: REPORT <<<")
        return self._finalize()

    # ====================================
    # RECALL — Use past memory (NEW - Hermes)
    # ====================================

    def _recall_memory(self):
        """Agent recalls what it learned in previous sessions"""
        past_failures = self.memory.data.get("failures", [])
        past_skills = self.memory.data.get("learned_skills", [])
        known_selectors = self.memory.data.get("working_selectors", {})

        log(f"Agent remembers {len(past_skills)} skills from past sessions")
        log(f"Agent remembers {len(known_selectors)} working selectors")

        recent_failures = [f for f in past_failures if f.get("session", 0) == self.memory.data["sessions"] - 1]
        if recent_failures:
            log(f"Agent recalls {len(recent_failures)} failures from last session:")
            for f in recent_failures:
                log(f"  - {f['test']}: {f['reason']}")
            log("Agent will PRIORITIZE re-testing these areas")
        else:
            log("No failures from last session — all was stable")

        for skill in past_skills:
            if skill["name"] in ["navigation_issue", "button_issue"]:
                log(f"Agent recalls insight: {skill['name']} -> {skill.get('steps', {}).get('suggestion', '')}")
                log("Agent will apply longer waits for this session")

    # ====================================
    # PERCEIVE — Understand the app
    # ====================================

    def _perceive(self):
        log("Agent is perceiving the application...")

        known_user_sel = self.memory.get_known_selector("username")
        known_pass_sel = self.memory.get_known_selector("password")

        if known_user_sel and known_pass_sel:
            log(f"Agent using REMEMBERED selectors:")
            log(f"  Username: {known_user_sel}")
            log(f"  Password: {known_pass_sel}")

        login_ok = self.executor.login()
        if not login_ok:
            return False

        login_result = self.validator.validate_login()
        if not login_result["overall"]:
            return False

        self.memory.remember_selector("username", self.executor.last_used_selector.get("username", ""))
        self.memory.remember_selector("password", self.executor.last_used_selector.get("password", ""))
        self.memory.remember_selector("submit", self.executor.last_used_selector.get("submit", ""))

        self.memory.learn_skill("login", {
            "url": self.app_url,
            "method": "form_fill",
            "success": True,
            "session": self.memory.data["sessions"]
        })

        self.executor.take_screenshot("03_dashboard")
        log(f"Agent is now at: {self.executor.get_current_url()}")

        links = self.planner.discover_links()
        if links:
            for link in links:
                self.memory.remember_page(link["text"], {"url": link["url"]})

        self.planner.build_page_map(self.executor)

        log(f"Agent perceives {len(self.planner.page_map)} pages in the app")
        return True

    # ====================================
    # PLAN — Generate + prioritize tests
    # ====================================

    def _plan(self):
        log("Agent is planning tests...")

        try:
            dashboard_url = self.app_url.replace("/login", "/app/dashboard") if "/login" in self.app_url else self.app_url
            self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)
        except Exception:
            pass

        tests = self.planner.generate_test_cases()

        past_failures = self.memory.data.get("failures", [])
        failed_names = set(f["test"] for f in past_failures)

        if failed_names:
            log(f"Agent is PRIORITIZING {len(failed_names)} previously failed test areas")

            priority_tests = []
            normal_tests = []

            for t in tests:
                if t["name"] in failed_names:
                    t["priority"] = "HIGH"
                    t["reason"] = "Failed in previous session"
                    priority_tests.append(t)
                else:
                    t["priority"] = "NORMAL"
                    normal_tests.append(t)

            tests = priority_tests + normal_tests

            log(f"Reordered: {len(priority_tests)} HIGH priority + {len(normal_tests)} NORMAL")

        log(f"Agent planned {len(tests)} test cases")
        log(f"Categories: {set(t['category'] for t in tests)}")

        return tests

    # ====================================
    # ACT + OBSERVE + REMEMBER
    # ====================================

    def _execute_all_tests(self, tests):
        total = len(tests)
        log(f"Agent is executing {total} tests...")
        log("=" * 60)

        needs_extra_wait = self.memory.get_skill("button_issue") is not None
        if needs_extra_wait:
            log("Agent applying LEARNED behavior: extra waits for buttons")

        for i, test in enumerate(tests):
            test_id = test["id"]
            test_name = test["name"]
            priority = test.get("priority", "NORMAL")

            priority_tag = " [HIGH PRIORITY - previously failed]" if priority == "HIGH" else ""
            log(f"\n[{i+1}/{total}] Running: {test_id} - {test_name}{priority_tag}")

            if needs_extra_wait and test["type"] == "button_click":
                try:
                    self.page.wait_for_timeout(2000)
                except Exception:
                    pass

            result = self.executor.run_test(test)

            status = result["status"]
            details = result["details"]

            if status == "FAIL" and test["type"] in ["button_click", "page_load", "input_fill"]:
                log(f"  RETRY: Self-healing attempt with longer wait...")
                try:
                    self.page.wait_for_timeout(3000)
                    result = self.executor.run_test(test)
                    status = result["status"]
                    details = result["details"]
                    if status == "PASS":
                        log(f"  SELF-HEALED: Test passed on retry!")
                        self.memory.learn_skill(f"retry_works_{test['type']}", {
                            "pattern": "needs_longer_wait",
                            "test_type": test["type"]
                        })
                except Exception:
                    pass

            icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
            log(f"  [{icon}] {status}: {details}")

            if status == "FAIL":
                safe_name = "".join(c if c.isalnum() else "_" for c in test_name)[:40]
                self.executor.take_screenshot(f"fail_{test_id}_{safe_name}")

            self.memory.remember_test_result(test_id, test_name, status, details)

            if status == "FAIL":
                self.memory.remember_failure(test_name, details)

            self.test_results.append({
                "id": test_id,
                "name": test_name,
                "category": test["category"],
                "status": status,
                "details": details,
                "priority": priority
            })

        log("\n" + "=" * 60)
        log("All tests executed")

    # ====================================
    # ADAPT — Learn from THIS session
    # ====================================

    def _adapt(self):
        log("Agent is analyzing results and adapting...")

        # HERMES: LLM Analysis (runs AFTER all tests)
        try:
            from agent.llm import analyze_after_tests
            log("\n>>> LLM ANALYSIS <<<")
            analysis = analyze_after_tests(self.test_results, self.memory.data)
            log(analysis)
            log(">>> END LLM ANALYSIS <<<\n")
            self.memory.learn_skill("llm_analysis", {
                "analysis": analysis[:500],
                "session": self.memory.data["sessions"]
            })
        except Exception as e:
            log(f"LLM analysis skipped: {str(e)[:100]}", level="WARN")

        failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]
        passed_tests = [t for t in self.test_results if t["status"] == "PASS"]

        for t in passed_tests:
            if t["category"] == "Navigation":
                self.memory.learn_skill(
                    f"navigate_{t['name']}",
                    {"type": "navigation", "status": "stable", "session": self.memory.data["sessions"]}
                )

        past_failures = self.memory.data.get("failures", [])
        last_session = self.memory.data["sessions"] - 1
        last_failed_names = set(
            f["test"] for f in past_failures if f.get("session", 0) == last_session
        )
        current_failed_names = set(f["name"] for f in failed_tests)

        fixed_tests = last_failed_names - current_failed_names
        if fixed_tests:
            log(f"LEARNING: {len(fixed_tests)} previously failing tests now PASS:")
            for ft in fixed_tests:
                log(f"  FIXED: {ft}")
            self.memory.learn_skill("self_improvement", {
                "fixed_count": len(fixed_tests),
                "session": self.memory.data["sessions"]
            })

        new_failures = current_failed_names - last_failed_names
        if new_failures:
            log(f"LEARNING: {len(new_failures)} NEW failures detected (regression):")
            for nf in new_failures:
                log(f"  NEW FAILURE: {nf}")
            self.memory.learn_skill("regression_detected", {
                "new_failure_count": len(new_failures),
                "session": self.memory.data["sessions"]
            })

        if failed_tests:
            log(f"Agent detected {len(failed_tests)} failures:")
            for f in failed_tests:
                log(f"  - {f['name']}: {f['details']}")

            categories = [f["category"] for f in failed_tests]
            if categories.count("Navigation") > 2:
                log("  INSIGHT: Multiple navigation failures — possible app issue")
                self.memory.learn_skill("navigation_issue", {
                    "pattern": "multiple_nav_failures",
                    "suggestion": "check if app is responsive"
                })

            if categories.count("Button") > 2:
                log("  INSIGHT: Multiple button failures — possible JS loading issue")
                self.memory.learn_skill("button_issue", {
                    "pattern": "multiple_button_failures",
                    "suggestion": "increase wait times"
                })

            if categories.count("Console") > 2:
                log("  INSIGHT: Multiple console errors — possible frontend bug")
                self.memory.learn_skill("console_issue", {
                    "pattern": "multiple_console_errors",
                    "suggestion": "check JS errors in dev tools"
                })
        else:
            log("No failures — all tests passed!")

        log(f"Agent has {len(self.memory.data['learned_skills'])} skills in memory")

    # ====================================
    # FINALIZE — Report + save
    # ====================================

    def _finalize(self):
        summary = self.memory.get_summary()

        log("=" * 60)
        log("FINAL AGENT REPORT")
        log("=" * 60)
        log(f"Session: #{summary['session']}")
        log(f"Total Tests: {summary['total_tests']}")
        log(f"Passed: {summary['passed']}")
        log(f"Failed: {summary['failed']}")
        log(f"Skipped: {summary['skipped']}")
        log(f"Pass Rate: {summary['pass_rate']}")
        log(f"Skills Learned: {summary['skills_learned']}")
        log("=" * 60)

        reporter = Reporter(
            test_results=self.test_results,
            memory=self.memory,
            page_map=self.planner.page_map
        )
        reporter.generate_all()

        self.memory.save()

        return summary



# import json
# import os
# from utils.logger import log
# from agent.executor import Executor
# from agent.validator import Validator
# from agent.planner import Planner
# from agent.memory import Memory
# from agent.reporter import Reporter
# import config
# #from agent.llm import analyze_results, explain_failure, suggest_new_tests, suggest_healing_strategy


# class Brain:
#     """
#     The Agent Brain — Hermes-inspired autonomous testing agent.
#     PERCEIVE -> PLAN -> ACT -> OBSERVE -> REMEMBER -> ADAPT -> REPORT
#     Now with REAL learning across sessions.
#     """

#     def __init__(self, page):
#         self.page = page
#         self.executor = Executor(page)
#         self.validator = Validator(page)
#         self.planner = Planner(page)
#         self.memory = Memory()
#         self.test_results = []

#     def run(self):
#         log("*" * 60)
#         log("*    HERMES-INSPIRED APA TESTING AGENT    *")
#         log("*" * 60)

#         self.memory.increment_session()
#         session = self.memory.data["sessions"]

#         # Show what agent remembers from past
#         if session > 1:
#             log(f"\n>>> AGENT MEMORY RECALL (Session #{session}) <<<")
#             self._recall_memory()

#         log("\n>>> AGENT PHASE: PERCEIVE <<<")
#         login_ok = self._perceive()
#         if not login_ok:
#             log("Agent cannot proceed without login", level="ERROR")
#             return self._finalize()

#         log("\n>>> AGENT PHASE: PLAN <<<")
#         tests = self._plan()
#         if not tests:
#             log("Agent has no tests to run", level="WARN")
#             return self._finalize()

#         log("\n>>> AGENT PHASE: ACT + OBSERVE + REMEMBER <<<")
#         self._execute_all_tests(tests)

#         log("\n>>> AGENT PHASE: ADAPT <<<")
#         self._adapt()

#         log("\n>>> AGENT PHASE: REPORT <<<")
#         return self._finalize()

#     # ====================================
#     # RECALL — Use past memory (NEW - Hermes)
#     # ====================================

#     def _recall_memory(self):
#         """Agent recalls what it learned in previous sessions"""
#         past_failures = self.memory.data.get("failures", [])
#         past_skills = self.memory.data.get("learned_skills", [])
#         known_selectors = self.memory.data.get("working_selectors", {})

#         log(f"Agent remembers {len(past_skills)} skills from past sessions")
#         log(f"Agent remembers {len(known_selectors)} working selectors")

#         # Identify previously failed tests
#         recent_failures = [f for f in past_failures if f.get("session", 0) == self.memory.data["sessions"] - 1]
#         if recent_failures:
#             log(f"Agent recalls {len(recent_failures)} failures from last session:")
#             for f in recent_failures:
#                 log(f"  - {f['test']}: {f['reason']}")
#             log("Agent will PRIORITIZE re-testing these areas")
#         else:
#             log("No failures from last session — all was stable")

#         # Check if agent learned any insights
#         for skill in past_skills:
#             if skill["name"] in ["navigation_issue", "button_issue"]:
#                 log(f"Agent recalls insight: {skill['name']} -> {skill.get('steps', {}).get('suggestion', '')}")
#                 log("Agent will apply longer waits for this session")

#     # ====================================
#     # PERCEIVE — Understand the app
#     # ====================================

#     def _perceive(self):
#         log("Agent is perceiving the application...")

#         # Use remembered selectors for login (Hermes: reuse learned skills)
#         known_user_sel = self.memory.get_known_selector("username")
#         known_pass_sel = self.memory.get_known_selector("password")

#         if known_user_sel and known_pass_sel:
#             log(f"Agent using REMEMBERED selectors:")
#             log(f"  Username: {known_user_sel}")
#             log(f"  Password: {known_pass_sel}")

#         login_ok = self.executor.login()
#         if not login_ok:
#             return False

#         login_result = self.validator.validate_login()
#         if not login_result["overall"]:
#             return False

#         # Remember working login selectors for next session
#         self.memory.remember_selector("username", self.executor.last_used_selector.get("username", ""))
#         self.memory.remember_selector("password", self.executor.last_used_selector.get("password", ""))
#         self.memory.remember_selector("submit", self.executor.last_used_selector.get("submit", ""))

#         self.memory.learn_skill("login", {
#             "url": config.APP_URL,
#             "method": "form_fill",
#             "success": True,
#             "session": self.memory.data["sessions"]
#         })

#         self.executor.take_screenshot("03_dashboard")
#         log(f"Agent is now at: {self.executor.get_current_url()}")

#         links = self.planner.discover_links()
#         if links:
#             for link in links:
#                 self.memory.remember_page(link["text"], {"url": link["url"]})

#         self.planner.build_page_map(self.executor)

#         log(f"Agent perceives {len(self.planner.page_map)} pages in the app")
#         return True

#     # ====================================
#     # PLAN — Generate + prioritize tests
#     # ====================================

#     def _plan(self):
#         log("Agent is planning tests...")

#         try:
#             dashboard_url = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/dashboard"
#             self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)
#         except Exception:
#             pass

#         tests = self.planner.generate_test_cases()

#         # HERMES LEARNING: Prioritize previously failed tests
#         past_failures = self.memory.data.get("failures", [])
#         failed_names = set(f["test"] for f in past_failures)

#         if failed_names:
#             log(f"Agent is PRIORITIZING {len(failed_names)} previously failed test areas")

#             priority_tests = []
#             normal_tests = []

#             for t in tests:
#                 if t["name"] in failed_names:
#                     t["priority"] = "HIGH"
#                     t["reason"] = "Failed in previous session"
#                     priority_tests.append(t)
#                 else:
#                     t["priority"] = "NORMAL"
#                     normal_tests.append(t)

#             tests = priority_tests + normal_tests

#             log(f"Reordered: {len(priority_tests)} HIGH priority + {len(normal_tests)} NORMAL")

#         log(f"Agent planned {len(tests)} test cases")
#         log(f"Categories: {set(t['category'] for t in tests)}")

#         return tests

#     # ====================================
#     # ACT + OBSERVE + REMEMBER
#     # ====================================

#     def _execute_all_tests(self, tests):
#         total = len(tests)
#         log(f"Agent is executing {total} tests...")
#         log("=" * 60)

#         # HERMES: Check if we should use longer waits
#         needs_extra_wait = self.memory.get_skill("button_issue") is not None
#         if needs_extra_wait:
#             log("Agent applying LEARNED behavior: extra waits for buttons")

#         for i, test in enumerate(tests):
#             test_id = test["id"]
#             test_name = test["name"]
#             priority = test.get("priority", "NORMAL")

#             priority_tag = " [HIGH PRIORITY - previously failed]" if priority == "HIGH" else ""
#             log(f"\n[{i+1}/{total}] Running: {test_id} - {test_name}{priority_tag}")

#             # HERMES: Apply learned wait behavior
#             if needs_extra_wait and test["type"] == "button_click":
#                 try:
#                     self.page.wait_for_timeout(2000)
#                 except Exception:
#                     pass

#             result = self.executor.run_test(test)

#             status = result["status"]
#             details = result["details"]

#             # HERMES: Self-healing — if test failed, retry once with longer wait
#             if status == "FAIL" and test["type"] in ["button_click", "page_load", "input_fill"]:
#                 log(f"  RETRY: Self-healing attempt with longer wait...")
#                 try:
#                     self.page.wait_for_timeout(3000)
#                     result = self.executor.run_test(test)
#                     status = result["status"]
#                     details = result["details"]
#                     if status == "PASS":
#                         log(f"  SELF-HEALED: Test passed on retry!")
#                         self.memory.learn_skill(f"retry_works_{test['type']}", {
#                             "pattern": "needs_longer_wait",
#                             "test_type": test["type"]
#                         })
#                 except Exception:
#                     pass

#             icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
#             log(f"  [{icon}] {status}: {details}")

#             if status == "FAIL":
#                 safe_name = "".join(c if c.isalnum() else "_" for c in test_name)[:40]
#                 self.executor.take_screenshot(f"fail_{test_id}_{safe_name}")

#             self.memory.remember_test_result(test_id, test_name, status, details)

#             if status == "FAIL":
#                 self.memory.remember_failure(test_name, details)

#             self.test_results.append({
#                 "id": test_id,
#                 "name": test_name,
#                 "category": test["category"],
#                 "status": status,
#                 "details": details,
#                 "priority": priority
#             })

#         log("\n" + "=" * 60)
#         log("All tests executed")

#     # ====================================
#     # ADAPT — Learn from THIS session
#     # ====================================

#     def _adapt(self):
#         log("Agent is analyzing results and adapting...")
#         # HERMES: LLM Analysis (runs AFTER all tests)
#         try:
#             from agent.llm import analyze_after_tests
#             log("\n>>> LLM ANALYSIS <<<")
#             analysis = analyze_after_tests(self.test_results, self.memory.data)
#             log(analysis)
#             log(">>> END LLM ANALYSIS <<<\n")
#             self.memory.learn_skill("llm_analysis", {
#                 "analysis": analysis[:500],
#                 "session": self.memory.data["sessions"]
#             })
#         except Exception as e:
#             log(f"LLM analysis skipped: {str(e)[:100]}", level="WARN")

#         failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]
#         passed_tests = [t for t in self.test_results if t["status"] == "PASS"]

#         # Learn navigation patterns
#         for t in passed_tests:
#             if t["category"] == "Navigation":
#                 self.memory.learn_skill(
#                     f"navigate_{t['name']}",
#                     {"type": "navigation", "status": "stable", "session": self.memory.data["sessions"]}
#                 )

#         # HERMES: Compare with last session
#         past_failures = self.memory.data.get("failures", [])
#         last_session = self.memory.data["sessions"] - 1
#         last_failed_names = set(
#             f["test"] for f in past_failures if f.get("session", 0) == last_session
#         )
#         current_failed_names = set(f["name"] for f in failed_tests)

#         # Tests that were failing but now pass = improvement
#         fixed_tests = last_failed_names - current_failed_names
#         if fixed_tests:
#             log(f"LEARNING: {len(fixed_tests)} previously failing tests now PASS:")
#             for ft in fixed_tests:
#                 log(f"  FIXED: {ft}")
#             self.memory.learn_skill("self_improvement", {
#                 "fixed_count": len(fixed_tests),
#                 "session": self.memory.data["sessions"]
#             })

#         # Tests that are newly failing = regression
#         new_failures = current_failed_names - last_failed_names
#         if new_failures:
#             log(f"LEARNING: {len(new_failures)} NEW failures detected (regression):")
#             for nf in new_failures:
#                 log(f"  NEW FAILURE: {nf}")
#             self.memory.learn_skill("regression_detected", {
#                 "new_failure_count": len(new_failures),
#                 "session": self.memory.data["sessions"]
#             })

#         # Pattern detection
#         if failed_tests:
#             log(f"Agent detected {len(failed_tests)} failures:")
#             for f in failed_tests:
#                 log(f"  - {f['name']}: {f['details']}")

#             categories = [f["category"] for f in failed_tests]
#             if categories.count("Navigation") > 2:
#                 log("  INSIGHT: Multiple navigation failures — possible app issue")
#                 self.memory.learn_skill("navigation_issue", {
#                     "pattern": "multiple_nav_failures",
#                     "suggestion": "check if app is responsive"
#                 })

#             if categories.count("Button") > 2:
#                 log("  INSIGHT: Multiple button failures — possible JS loading issue")
#                 self.memory.learn_skill("button_issue", {
#                     "pattern": "multiple_button_failures",
#                     "suggestion": "increase wait times"
#                 })

#             if categories.count("Console") > 2:
#                 log("  INSIGHT: Multiple console errors — possible frontend bug")
#                 self.memory.learn_skill("console_issue", {
#                     "pattern": "multiple_console_errors",
#                     "suggestion": "check JS errors in dev tools"
#                 })
#         else:
#             log("No failures — all tests passed!")

#         log(f"Agent has {len(self.memory.data['learned_skills'])} skills in memory")

#     # ====================================
#     # FINALIZE — Report + save
#     # ====================================

#     def _finalize(self):
#         summary = self.memory.get_summary()

#         log("=" * 60)
#         log("FINAL AGENT REPORT")
#         log("=" * 60)
#         log(f"Session: #{summary['session']}")
#         log(f"Total Tests: {summary['total_tests']}")
#         log(f"Passed: {summary['passed']}")
#         log(f"Failed: {summary['failed']}")
#         log(f"Skipped: {summary['skipped']}")
#         log(f"Pass Rate: {summary['pass_rate']}")
#         log(f"Skills Learned: {summary['skills_learned']}")
#         log("=" * 60)

#         reporter = Reporter(
#             test_results=self.test_results,
#             memory=self.memory,
#             page_map=self.planner.page_map
#         )
#         reporter.generate_all()

#         self.memory.save()

#         return summary











# LLM Integration code below

# import json
# import os
# from utils.logger import log
# from agent.executor import Executor
# from agent.validator import Validator
# from agent.planner import Planner
# from agent.memory import Memory
# from agent.reporter import Reporter
# import config
# from agent.llm import analyze_results, explain_failure, suggest_new_tests, suggest_healing_strategy


# class Brain:
#     """
#     The Agent Brain — Hermes-inspired autonomous testing agent.
#     PERCEIVE -> PLAN -> ACT -> OBSERVE -> REMEMBER -> ADAPT -> REPORT
#     Now with REAL learning across sessions + LLM reasoning.
#     """

#     def __init__(self, page):
#         self.page = page
#         self.executor = Executor(page)
#         self.validator = Validator(page)
#         self.planner = Planner(page)
#         self.memory = Memory()
#         self.test_results = []

#     def run(self):
#         log("*" * 60)
#         log("*    HERMES-INSPIRED APA TESTING AGENT    *")
#         log("*" * 60)

#         self.memory.increment_session()
#         session = self.memory.data["sessions"]

#         if session > 1:
#             log(f"\n>>> AGENT MEMORY RECALL (Session #{session}) <<<")
#             self._recall_memory()

#         log("\n>>> AGENT PHASE: PERCEIVE <<<")
#         login_ok = self._perceive()
#         if not login_ok:
#             log("Agent cannot proceed without login", level="ERROR")
#             return self._finalize()

#         log("\n>>> AGENT PHASE: PLAN <<<")
#         tests = self._plan()
#         if not tests:
#             log("Agent has no tests to run", level="WARN")
#             return self._finalize()

#         log("\n>>> AGENT PHASE: ACT + OBSERVE + REMEMBER <<<")
#         self._execute_all_tests(tests)

#         log("\n>>> AGENT PHASE: ADAPT <<<")
#         self._adapt()

#         log("\n>>> AGENT PHASE: REPORT <<<")
#         return self._finalize()

#     # ====================================
#     # RECALL — Use past memory
#     # ====================================

#     def _recall_memory(self):
#         past_failures = self.memory.data.get("failures", [])
#         past_skills = self.memory.data.get("learned_skills", [])
#         known_selectors = self.memory.data.get("working_selectors", {})

#         log(f"Agent remembers {len(past_skills)} skills from past sessions")
#         log(f"Agent remembers {len(known_selectors)} working selectors")

#         recent_failures = [f for f in past_failures if f.get("session", 0) == self.memory.data["sessions"] - 1]
#         if recent_failures:
#             log(f"Agent recalls {len(recent_failures)} failures from last session:")
#             for f in recent_failures:
#                 log(f"  - {f['test']}: {f['reason']}")
#             log("Agent will PRIORITIZE re-testing these areas")
#         else:
#             log("No failures from last session — all was stable")

#         for skill in past_skills:
#             if skill["name"] in ["navigation_issue", "button_issue"]:
#                 log(f"Agent recalls insight: {skill['name']} -> {skill.get('steps', {}).get('suggestion', '')}")
#                 log("Agent will apply longer waits for this session")

#     # ====================================
#     # PERCEIVE — Understand the app
#     # ====================================

#     def _perceive(self):
#         log("Agent is perceiving the application...")

#         known_user_sel = self.memory.get_known_selector("username")
#         known_pass_sel = self.memory.get_known_selector("password")

#         if known_user_sel and known_pass_sel:
#             log(f"Agent using REMEMBERED selectors:")
#             log(f"  Username: {known_user_sel}")
#             log(f"  Password: {known_pass_sel}")

#         login_ok = self.executor.login()
#         if not login_ok:
#             return False

#         login_result = self.validator.validate_login()
#         if not login_result["overall"]:
#             return False

#         self.memory.remember_selector("username", self.executor.last_used_selector.get("username", ""))
#         self.memory.remember_selector("password", self.executor.last_used_selector.get("password", ""))
#         self.memory.remember_selector("submit", self.executor.last_used_selector.get("submit", ""))

#         self.memory.learn_skill("login", {
#             "url": config.APP_URL,
#             "method": "form_fill",
#             "success": True,
#             "session": self.memory.data["sessions"]
#         })

#         self.executor.take_screenshot("03_dashboard")
#         log(f"Agent is now at: {self.executor.get_current_url()}")

#         links = self.planner.discover_links()
#         if links:
#             for link in links:
#                 self.memory.remember_page(link["text"], {"url": link["url"]})

#         self.planner.build_page_map(self.executor)

#         log(f"Agent perceives {len(self.planner.page_map)} pages in the app")
#         return True

#     # ====================================
#     # PLAN — Generate + prioritize tests
#     # ====================================

#     def _plan(self):
#         log("Agent is planning tests...")

#         try:
#             dashboard_url = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/dashboard"
#             self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)
#         except Exception:
#             pass

#         tests = self.planner.generate_test_cases()

#         past_failures = self.memory.data.get("failures", [])
#         failed_names = set(f["test"] for f in past_failures)

#         if failed_names:
#             log(f"Agent is PRIORITIZING {len(failed_names)} previously failed test areas")

#             priority_tests = []
#             normal_tests = []

#             for t in tests:
#                 if t["name"] in failed_names:
#                     t["priority"] = "HIGH"
#                     t["reason"] = "Failed in previous session"
#                     priority_tests.append(t)
#                 else:
#                     t["priority"] = "NORMAL"
#                     normal_tests.append(t)

#             tests = priority_tests + normal_tests

#             log(f"Reordered: {len(priority_tests)} HIGH priority + {len(normal_tests)} NORMAL")

#         log(f"Agent planned {len(tests)} test cases")
#         log(f"Categories: {set(t['category'] for t in tests)}")

#         return tests

#     # ====================================
#     # ACT + OBSERVE + REMEMBER (with LLM self-healing)
#     # ====================================

#     def _execute_all_tests(self, tests):
#         total = len(tests)
#         log(f"Agent is executing {total} tests...")
#         log("=" * 60)

#         needs_extra_wait = self.memory.get_skill("button_issue") is not None
#         if needs_extra_wait:
#             log("Agent applying LEARNED behavior: extra waits for buttons")

#         for i, test in enumerate(tests):
#             test_id = test["id"]
#             test_name = test["name"]
#             priority = test.get("priority", "NORMAL")

#             priority_tag = " [HIGH PRIORITY - previously failed]" if priority == "HIGH" else ""
#             log(f"\n[{i+1}/{total}] Running: {test_id} - {test_name}{priority_tag}")

#             if needs_extra_wait and test["type"] == "button_click":
#                 try:
#                     self.page.wait_for_timeout(2000)
#                 except Exception:
#                     pass

#             result = self.executor.run_test(test)

#             status = result["status"]
#             details = result["details"]

#             # ====================================
#             # HERMES + LLM: Intelligent Self-healing
#             # ====================================
#             if status == "FAIL":
#                 log(f"  LLM SELF-HEALING: Analyzing failure...")
#                 try:
#                     healing = suggest_healing_strategy(
#                         test_name=test_name,
#                         failure_details=details,
#                         test_type=test["type"],
#                         page_url=test.get("target_url", ""),
#                         past_attempts=0
#                     )

#                     log(f"  LLM Strategy: {healing.get('strategy', 'unknown')}")
#                     log(f"  Should retry: {healing.get('should_retry', False)}")
#                     log(f"  Wait: {healing.get('wait_seconds', 0)}s")
#                     log(f"  Real bug: {healing.get('is_real_bug', False)}")

#                     if healing.get("should_retry", False):
#                         wait_ms = healing.get("wait_seconds", 3) * 1000
#                         log(f"  RETRY: Waiting {healing.get('wait_seconds', 3)}s as LLM suggested...")
#                         self.page.wait_for_timeout(wait_ms)
#                         result = self.executor.run_test(test)
#                         status = result["status"]
#                         details = result["details"]
#                         if status == "PASS":
#                             log(f"  SELF-HEALED after LLM-suggested wait!")
#                             self.memory.learn_skill(f"llm_healed_{test['type']}", {
#                                 "healing_strategy": healing.get("strategy", ""),
#                                 "wait_used": healing.get("wait_seconds", 3),
#                                 "session": self.memory.data["sessions"]
#                             })
#                     else:
#                         if healing.get("is_real_bug", False):
#                             log(f"  LLM says: REAL BUG — not retrying")
#                             self.memory.learn_skill(f"real_bug_{test_name[:30]}", {
#                                 "test": test_name,
#                                 "reason": healing.get("strategy", ""),
#                                 "session": self.memory.data["sessions"]
#                             })
#                         else:
#                             log(f"  LLM says: Skip retry — {healing.get('strategy', '')}")

#                 except Exception as e:
#                     log(f"  LLM healing failed, default retry: {str(e)[:100]}")
#                     if test["type"] in ["button_click", "page_load", "input_fill"]:
#                         try:
#                             self.page.wait_for_timeout(3000)
#                             result = self.executor.run_test(test)
#                             status = result["status"]
#                             details = result["details"]
#                             if status == "PASS":
#                                 log(f"  SELF-HEALED on default retry!")
#                                 self.memory.learn_skill(f"retry_works_{test['type']}", {
#                                     "pattern": "needs_longer_wait",
#                                     "test_type": test["type"]
#                                 })
#                         except Exception:
#                             pass

#             icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
#             log(f"  [{icon}] {status}: {details}")

#             if status == "FAIL":
#                 safe_name = "".join(c if c.isalnum() else "_" for c in test_name)[:40]
#                 self.executor.take_screenshot(f"fail_{test_id}_{safe_name}")

#             self.memory.remember_test_result(test_id, test_name, status, details)

#             if status == "FAIL":
#                 self.memory.remember_failure(test_name, details)

#             self.test_results.append({
#                 "id": test_id,
#                 "name": test_name,
#                 "category": test["category"],
#                 "status": status,
#                 "details": details,
#                 "priority": priority
#             })

#         log("\n" + "=" * 60)
#         log("All tests executed")

#     # ====================================
#     # ADAPT — Learn from THIS session + LLM reasoning
#     # ====================================

#     def _adapt(self):
#         log("Agent is analyzing results and adapting...")

#         # ====================================
#         # HERMES: LLM Reasoning
#         # ====================================
#         try:
#             log("\n>>> LLM ANALYSIS <<<")
#             analysis = analyze_results(self.test_results, self.memory.data)
#             log(analysis)
#             log(">>> END LLM ANALYSIS <<<\n")

#             failed_tests_llm = [t for t in self.test_results if t["status"] == "FAIL"]
#             for f in failed_tests_llm:
#                 log(f"\n>>> LLM FAILURE ANALYSIS: {f['name']} <<<")
#                 explanation = explain_failure(f["name"], f["details"], "")
#                 log(explanation)
#                 log(">>>\n")

#             if self.planner.page_map:
#                 log("\n>>> LLM TEST SUGGESTIONS <<<")
#                 suggestions = suggest_new_tests(
#                     [{"name": p["page_name"], "url": p["url"]} for p in self.planner.page_map],
#                     self.memory.data.get("failures", [])
#                 )
#                 log(suggestions)
#                 self.memory.learn_skill("llm_suggestions", {
#                     "suggestions": suggestions[:500],
#                     "session": self.memory.data["sessions"]
#                 })
#                 log(">>> END LLM SUGGESTIONS <<<\n")

#         except Exception as e:
#             log(f"LLM reasoning skipped: {str(e)[:100]}", level="WARN")

#         # ====================================
#         # Existing rule-based adaptation
#         # ====================================
#         failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]
#         passed_tests = [t for t in self.test_results if t["status"] == "PASS"]

#         for t in passed_tests:
#             if t["category"] == "Navigation":
#                 self.memory.learn_skill(
#                     f"navigate_{t['name']}",
#                     {"type": "navigation", "status": "stable", "session": self.memory.data["sessions"]}
#                 )

#         past_failures = self.memory.data.get("failures", [])
#         last_session = self.memory.data["sessions"] - 1
#         last_failed_names = set(
#             f["test"] for f in past_failures if f.get("session", 0) == last_session
#         )
#         current_failed_names = set(f["name"] for f in failed_tests)

#         fixed_tests = last_failed_names - current_failed_names
#         if fixed_tests:
#             log(f"LEARNING: {len(fixed_tests)} previously failing tests now PASS:")
#             for ft in fixed_tests:
#                 log(f"  FIXED: {ft}")
#             self.memory.learn_skill("self_improvement", {
#                 "fixed_count": len(fixed_tests),
#                 "session": self.memory.data["sessions"]
#             })

#         new_failures = current_failed_names - last_failed_names
#         if new_failures:
#             log(f"LEARNING: {len(new_failures)} NEW failures detected (regression):")
#             for nf in new_failures:
#                 log(f"  NEW FAILURE: {nf}")
#             self.memory.learn_skill("regression_detected", {
#                 "new_failure_count": len(new_failures),
#                 "session": self.memory.data["sessions"]
#             })

#         if failed_tests:
#             log(f"Agent detected {len(failed_tests)} failures:")
#             for f in failed_tests:
#                 log(f"  - {f['name']}: {f['details']}")

#             categories = [f["category"] for f in failed_tests]
#             if categories.count("Navigation") > 2:
#                 log("  INSIGHT: Multiple navigation failures — possible app issue")
#                 self.memory.learn_skill("navigation_issue", {
#                     "pattern": "multiple_nav_failures",
#                     "suggestion": "check if app is responsive"
#                 })

#             if categories.count("Button") > 2:
#                 log("  INSIGHT: Multiple button failures — possible JS loading issue")
#                 self.memory.learn_skill("button_issue", {
#                     "pattern": "multiple_button_failures",
#                     "suggestion": "increase wait times"
#                 })

#             if categories.count("Console") > 2:
#                 log("  INSIGHT: Multiple console errors — possible frontend bug")
#                 self.memory.learn_skill("console_issue", {
#                     "pattern": "multiple_console_errors",
#                     "suggestion": "check JS errors in dev tools"
#                 })
#         else:
#             log("No failures — all tests passed!")

#         log(f"Agent has {len(self.memory.data['learned_skills'])} skills in memory")

#     # ====================================
#     # FINALIZE — Report + save
#     # ====================================

#     def _finalize(self):
#         summary = self.memory.get_summary()

#         log("=" * 60)
#         log("FINAL AGENT REPORT")
#         log("=" * 60)
#         log(f"Session: #{summary['session']}")
#         log(f"Total Tests: {summary['total_tests']}")
#         log(f"Passed: {summary['passed']}")
#         log(f"Failed: {summary['failed']}")
#         log(f"Skipped: {summary['skipped']}")
#         log(f"Pass Rate: {summary['pass_rate']}")
#         log(f"Skills Learned: {summary['skills_learned']}")
#         log("=" * 60)

#         reporter = Reporter(
#             test_results=self.test_results,
#             memory=self.memory,
#             page_map=self.planner.page_map
#         )
#         reporter.generate_all()

#         self.memory.save()

#         return summary








# import json
# import os
# from utils.logger import log
# from agent.executor import Executor
# from agent.validator import Validator
# from agent.planner import Planner
# from agent.memory import Memory
# from agent.reporter import Reporter
# import config


# class Brain:
#     """
#     The Agent Brain — Hermes-inspired autonomous testing agent.
#     Follows: PERCEIVE -> PLAN -> ACT -> OBSERVE -> REMEMBER -> ADAPT -> REPORT
#     """

#     def __init__(self, page):
#         self.page = page
#         self.executor = Executor(page)
#         self.validator = Validator(page)
#         self.planner = Planner(page)
#         self.memory = Memory()
#         self.test_results = []

#     def run(self):
#         log("*" * 60)
#         log("*    HERMES-INSPIRED APA TESTING AGENT    *")
#         log("*" * 60)

#         self.memory.increment_session()

#         log("\n>>> AGENT PHASE: PERCEIVE <<<")
#         login_ok = self._perceive()
#         if not login_ok:
#             log("Agent cannot proceed without login", level="ERROR")
#             return self._finalize()

#         log("\n>>> AGENT PHASE: PLAN <<<")
#         tests = self._plan()
#         if not tests:
#             log("Agent has no tests to run", level="WARN")
#             return self._finalize()

#         log("\n>>> AGENT PHASE: ACT + OBSERVE + REMEMBER <<<")
#         self._execute_all_tests(tests)

#         log("\n>>> AGENT PHASE: ADAPT <<<")
#         self._adapt()

#         log("\n>>> AGENT PHASE: REPORT <<<")
#         return self._finalize()

#     def _perceive(self):
#         log("Agent is perceiving the application...")

#         login_ok = self.executor.login()
#         if not login_ok:
#             return False

#         login_result = self.validator.validate_login()
#         if not login_result["overall"]:
#             return False

#         self.memory.learn_skill("login", {
#             "url": config.APP_URL,
#             "method": "form_fill",
#             "success": True
#         })

#         self.executor.take_screenshot("03_dashboard")
#         log(f"Agent is now at: {self.executor.get_current_url()}")

#         links = self.planner.discover_links()
#         if links:
#             for link in links:
#                 self.memory.remember_page(link["text"], {"url": link["url"]})

#         self.planner.build_page_map(self.executor)

#         log(f"Agent perceives {len(self.planner.page_map)} pages in the app")
#         return True

#     def _plan(self):
#         log("Agent is planning tests...")

#         try:
#             dashboard_url = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/dashboard"
#             self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)
#         except Exception:
#             pass

#         tests = self.planner.generate_test_cases()

#         log(f"Agent planned {len(tests)} test cases")
#         log(f"Categories: {set(t['category'] for t in tests)}")

#         return tests

#     def _execute_all_tests(self, tests):
#         total = len(tests)
#         log(f"Agent is executing {total} tests...")
#         log("=" * 60)

#         for i, test in enumerate(tests):
#             test_id = test["id"]
#             test_name = test["name"]

#             log(f"\n[{i+1}/{total}] Running: {test_id} - {test_name}")

#             result = self.executor.run_test(test)

#             status = result["status"]
#             details = result["details"]

#             icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
#             log(f"  [{icon}] {status}: {details}")

#             if status == "FAIL":
#                 safe_name = "".join(c if c.isalnum() else "_" for c in test_name)[:40]
#                 self.executor.take_screenshot(f"fail_{test_id}_{safe_name}")

#             self.memory.remember_test_result(test_id, test_name, status, details)

#             if status == "FAIL":
#                 self.memory.remember_failure(test_name, details)

#             self.test_results.append({
#                 "id": test_id,
#                 "name": test_name,
#                 "category": test["category"],
#                 "status": status,
#                 "details": details
#             })

#         log("\n" + "=" * 60)
#         log("All tests executed")

#     def _adapt(self):
#         log("Agent is analyzing results and adapting...")

#         failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]
#         passed_tests = [t for t in self.test_results if t["status"] == "PASS"]

#         for t in passed_tests:
#             if t["category"] == "Navigation":
#                 self.memory.learn_skill(
#                     f"navigate_{t['name']}",
#                     {"type": "navigation", "status": "working"}
#                 )

#         if failed_tests:
#             log(f"Agent detected {len(failed_tests)} failures:")
#             for f in failed_tests:
#                 log(f"  - {f['name']}: {f['details']}")

#             categories = [f["category"] for f in failed_tests]
#             if categories.count("Navigation") > 2:
#                 log("  INSIGHT: Multiple navigation failures — possible app issue")
#                 self.memory.learn_skill("navigation_issue", {
#                     "pattern": "multiple_nav_failures",
#                     "suggestion": "check if app is responsive"
#                 })

#             if categories.count("Button") > 2:
#                 log("  INSIGHT: Multiple button failures — possible JS loading issue")
#                 self.memory.learn_skill("button_issue", {
#                     "pattern": "multiple_button_failures",
#                     "suggestion": "increase wait times"
#                 })
#         else:
#             log("No failures to analyze — all tests passed!")

#         log(f"Agent has {len(self.memory.data['learned_skills'])} skills in memory")

#     def _finalize(self):
#         summary = self.memory.get_summary()

#         log("=" * 60)
#         log("FINAL AGENT REPORT")
#         log("=" * 60)
#         log(f"Session: #{summary['session']}")
#         log(f"Total Tests: {summary['total_tests']}")
#         log(f"Passed: {summary['passed']}")
#         log(f"Failed: {summary['failed']}")
#         log(f"Skipped: {summary['skipped']}")
#         log(f"Pass Rate: {summary['pass_rate']}")
#         log(f"Skills Learned: {summary['skills_learned']}")
#         log("=" * 60)

#         # Generate reports using Reporter
#         reporter = Reporter(
#             test_results=self.test_results,
#             memory=self.memory,
#             page_map=self.planner.page_map
#         )
#         reporter.generate_all()

#         # Save memory
#         self.memory.save()

#         return summary



# import json
# import os
# from utils.logger import log
# from agent.executor import Executor
# from agent.validator import Validator
# from agent.planner import Planner
# from agent.memory import Memory
# import config


# class Brain:
#     """
#     The Agent Brain — Hermes-inspired autonomous testing agent.
#     Follows: PERCEIVE -> PLAN -> ACT -> OBSERVE -> REMEMBER -> ADAPT -> REPORT
#     """

#     def __init__(self, page):
#         self.page = page
#         self.executor = Executor(page)
#         self.validator = Validator(page)
#         self.planner = Planner(page)
#         self.memory = Memory()
#         self.test_results = []

#     def run(self):
#         log("*" * 60)
#         log("*    HERMES-INSPIRED APA TESTING AGENT    *")
#         log("*" * 60)

#         self.memory.increment_session()

#         log("\n>>> AGENT PHASE: PERCEIVE <<<")
#         login_ok = self._perceive()
#         if not login_ok:
#             log("Agent cannot proceed without login", level="ERROR")
#             return self._generate_report()

#         log("\n>>> AGENT PHASE: PLAN <<<")
#         tests = self._plan()
#         if not tests:
#             log("Agent has no tests to run", level="WARN")
#             return self._generate_report()

#         log("\n>>> AGENT PHASE: ACT + OBSERVE + REMEMBER <<<")
#         self._execute_all_tests(tests)

#         log("\n>>> AGENT PHASE: ADAPT <<<")
#         self._adapt()

#         log("\n>>> AGENT PHASE: REPORT <<<")
#         report = self._generate_report()

#         self.memory.save()

#         return report

#     def _perceive(self):
#         log("Agent is perceiving the application...")

#         login_ok = self.executor.login()
#         if not login_ok:
#             return False

#         login_result = self.validator.validate_login()
#         if not login_result["overall"]:
#             return False

#         self.memory.learn_skill("login", {
#             "url": config.APP_URL,
#             "method": "form_fill",
#             "success": True
#         })

#         self.executor.take_screenshot("03_dashboard")
#         log(f"Agent is now at: {self.executor.get_current_url()}")

#         links = self.planner.discover_links()
#         if links:
#             for link in links:
#                 self.memory.remember_page(link["text"], {"url": link["url"]})

#         self.planner.build_page_map(self.executor)

#         log(f"Agent perceives {len(self.planner.page_map)} pages in the app")
#         return True

#     def _plan(self):
#         log("Agent is planning tests...")

#         try:
#             dashboard_url = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/dashboard"
#             self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)
#         except Exception:
#             pass

#         tests = self.planner.generate_test_cases()

#         log(f"Agent planned {len(tests)} test cases")
#         log(f"Categories: {set(t['category'] for t in tests)}")

#         return tests

#     def _execute_all_tests(self, tests):
#         total = len(tests)
#         log(f"Agent is executing {total} tests...")
#         log("=" * 60)

#         for i, test in enumerate(tests):
#             test_id = test["id"]
#             test_name = test["name"]

#             log(f"\n[{i+1}/{total}] Running: {test_id} - {test_name}")

#             result = self.executor.run_test(test)

#             status = result["status"]
#             details = result["details"]

#             icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
#             log(f"  [{icon}] {status}: {details}")

#             if status == "FAIL":
#                 safe_name = "".join(c if c.isalnum() else "_" for c in test_name)[:40]
#                 self.executor.take_screenshot(f"fail_{test_id}_{safe_name}")

#             self.memory.remember_test_result(test_id, test_name, status, details)

#             if status == "FAIL":
#                 self.memory.remember_failure(test_name, details)

#             self.test_results.append({
#                 "id": test_id,
#                 "name": test_name,
#                 "category": test["category"],
#                 "status": status,
#                 "details": details
#             })

#         log("\n" + "=" * 60)
#         log("All tests executed")

#     def _adapt(self):
#         log("Agent is analyzing results and adapting...")

#         failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]
#         passed_tests = [t for t in self.test_results if t["status"] == "PASS"]

#         for t in passed_tests:
#             if t["category"] == "Navigation":
#                 self.memory.learn_skill(
#                     f"navigate_{t['name']}",
#                     {"type": "navigation", "status": "working"}
#                 )

#         if failed_tests:
#             log(f"Agent detected {len(failed_tests)} failures:")
#             for f in failed_tests:
#                 log(f"  - {f['name']}: {f['details']}")

#             categories = [f["category"] for f in failed_tests]
#             if categories.count("Navigation") > 2:
#                 log("  INSIGHT: Multiple navigation failures — possible app issue")
#                 self.memory.learn_skill("navigation_issue", {
#                     "pattern": "multiple_nav_failures",
#                     "suggestion": "check if app is responsive"
#                 })

#             if categories.count("Button") > 2:
#                 log("  INSIGHT: Multiple button failures — possible JS loading issue")
#                 self.memory.learn_skill("button_issue", {
#                     "pattern": "multiple_button_failures",
#                     "suggestion": "increase wait times"
#                 })
#         else:
#             log("No failures to analyze — all tests passed!")

#         log(f"Agent has {len(self.memory.data['learned_skills'])} skills in memory")

#     def _generate_report(self):
#         summary = self.memory.get_summary()

#         log("=" * 60)
#         log("FINAL AGENT REPORT")
#         log("=" * 60)
#         log(f"Session: #{summary['session']}")
#         log(f"Total Tests: {summary['total_tests']}")
#         log(f"Passed: {summary['passed']}")
#         log(f"Failed: {summary['failed']}")
#         log(f"Skipped: {summary['skipped']}")
#         log(f"Pass Rate: {summary['pass_rate']}")
#         log(f"Skills Learned: {summary['skills_learned']}")
#         log(f"Known Selectors: {summary['known_selectors']}")
#         log("=" * 60)

#         categories = {}
#         for r in self.test_results:
#             cat = r["category"]
#             if cat not in categories:
#                 categories[cat] = {"pass": 0, "fail": 0, "skip": 0}
#             categories[cat][r["status"].lower()] = categories[cat].get(r["status"].lower(), 0) + 1

#         log("\nCategory Breakdown:")
#         for cat, counts in categories.items():
#             log(f"  {cat}: PASS={counts.get('pass',0)} FAIL={counts.get('fail',0)} SKIP={counts.get('skip',0)}")

#         failed = [r for r in self.test_results if r["status"] == "FAIL"]
#         if failed:
#             log(f"\nFailed Tests ({len(failed)}):")
#             for f in failed:
#                 log(f"  [{f['id']}] {f['name']}")
#                 log(f"    Reason: {f['details']}")

#         report = {
#             "summary": summary,
#             "categories": categories,
#             "all_results": self.test_results,
#             "failed_details": failed,
#             "memory_snapshot": {
#                 "skills": len(self.memory.data["learned_skills"]),
#                 "known_pages": len(self.memory.data["known_pages"]),
#             }
#         }

#         os.makedirs(config.REPORT_DIR, exist_ok=True)
#         with open(f"{config.REPORT_DIR}/test_report.json", "w") as f:
#             json.dump(report, f, indent=2)
#         log(f"\nReport saved to {config.REPORT_DIR}/test_report.json")

#         return report



# import json
# import os
# from utils.logger import log
# from agent.executor import Executor
# from agent.validator import Validator
# from agent.planner import Planner
# from agent.memory import Memory
# import config

# class Brain:
#     """
#     The Agent Brain — Hermes-inspired autonomous testing agent.
#     Follows: PERCEIVE -> PLAN -> ACT -> OBSERVE -> REMEMBER -> ADAPT -> REPORT
#     """

#     def __init__(self, page):
#         self.page = page
#         self.executor = Executor(page)
#         self.validator = Validator(page)
#         self.planner = Planner(page)
#         self.memory = Memory()
#         self.test_results = []

#     def run(self):
#         """Main agent loop"""
#         log("*" * 60)
#         log("*    HERMES-INSPIRED APA TESTING AGENT    *")
#         log("*" * 60)

#         self.memory.increment_session()

#         # ---- PHASE A: PERCEIVE ----
#         log("\n>>> AGENT PHASE: PERCEIVE <<<")
#         login_ok = self._perceive()
#         if not login_ok:
#             log("Agent cannot proceed without login", level="ERROR")
#             return self._generate_report()

#         # ---- PHASE B: PLAN ----
#         log("\n>>> AGENT PHASE: PLAN <<<")
#         tests = self._plan()
#         if not tests:
#             log("Agent has no tests to run", level="WARN")
#             return self._generate_report()

#         # ---- PHASE C: ACT + OBSERVE + REMEMBER (per test) ----
#         log("\n>>> AGENT PHASE: ACT + OBSERVE + REMEMBER <<<")
#         self._execute_all_tests(tests)

#         # ---- PHASE D: ADAPT ----
#         log("\n>>> AGENT PHASE: ADAPT <<<")
#         self._adapt()

#         # ---- PHASE E: REPORT ----
#         log("\n>>> AGENT PHASE: REPORT <<<")
#         report = self._generate_report()

#         # Save memory
#         self.memory.save()

#         return report

#     # ====================================
#     # PERCEIVE — Understand the app
#     # ====================================

#     def _perceive(self):
#         """Login and discover the application"""
#         log("Agent is perceiving the application...")

#         # Step 1: Login
#         login_ok = self.executor.login()
#         if not login_ok:
#             return False

#         # Step 2: Validate login
#         login_result = self.validator.validate_login()
#         if not login_result["overall"]:
#             return False

#         # Remember successful login
#         self.memory.learn_skill("login", {
#             "url": config.APP_URL,
#             "method": "form_fill",
#             "success": True
#         })

#         self.executor.take_screenshot("03_dashboard")
#         log(f"Agent is now at: {self.executor.get_current_url()}")

#         # Step 3: Discover navigation
#         links = self.planner.discover_links()
#         if links:
#             for link in links:
#                 self.memory.remember_page(link["text"], {"url": link["url"]})

#         # Step 4: Build page map
#         self.planner.build_page_map(self.executor)

#         log(f"Agent perceives {len(self.planner.page_map)} pages in the app")
#         return True

#     # ====================================
#     # PLAN — Generate test cases
#     # ====================================

#     def _plan(self):
#         """Generate test cases based on what was perceived"""
#         log("Agent is planning tests...")

#         # Navigate back to dashboard before generating tests
#         try:
#             dashboard_url = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/dashboard"
#             self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)
#         except Exception:
#             pass

#         tests = self.planner.generate_test_cases()

#         log(f"Agent planned {len(tests)} test cases")
#         log(f"Categories: {set(t['category'] for t in tests)}")

#         return tests

#     # ====================================
#     # ACT + OBSERVE + REMEMBER — Execute tests
#     # ====================================

#     def _execute_all_tests(self, tests):
#         """Execute each test, observe result, remember outcome"""
#         total = len(tests)
#         log(f"Agent is executing {total} tests...")
#         log("=" * 60)

#         for i, test in enumerate(tests):
#             test_id = test["id"]
#             test_name = test["name"]

#             log(f"\n[{i+1}/{total}] Running: {test_id} - {test_name}")

#             # ACT: Execute the test
#             result = self.executor.run_test(test)

#             status = result["status"]
#             details = result["details"]

#             # OBSERVE: Log result
#             icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
#             log(f"  {icon} {status}: {details}")

#             # Take screenshot on failure
#             if status == "FAIL":
#                 safe_name = "".join(c if c.isalnum() else "_" for c in test_name)[:40]
#                 self.executor.take_screenshot(f"fail_{test_id}_{safe_name}")

#             # REMEMBER: Store result in memory
#             self.memory.remember_test_result(test_id, test_name, status, details)

#             if status == "FAIL":
#                 self.memory.remember_failure(test_name, details)

#             # Store for report
#             self.test_results.append({
#                 "id": test_id,
#                 "name": test_name,
#                 "category": test["category"],
#                 "status": status,
#                 "details": details
#             })

#         log("\n" + "=" * 60)
#         log("All tests executed")

#     # ====================================
#     # ADAPT — Learn from results
#     # ====================================

#     def _adapt(self):
#         """Analyze results and adapt/learn"""
#         log("Agent is analyzing results and adapting...")

#         failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]
#         passed_tests = [t for t in self.test_results if t["status"] == "PASS"]

#         # Learn patterns from successful tests
#         for t in passed_tests:
#             if t["category"] == "Navigation":
#                 self.memory.learn_skill(
#                     f"navigate_{t['name']}",
#                     {"type": "navigation", "status": "working"}
#                 )

#         # Analyze failures for patterns
#         if failed_tests:
#             log(f"Agent detected {len(failed_tests)} failures:")
#             for f in failed_tests:
#                 log(f"  - {f['name']}: {f['details']}")

#             # Check if failures are related
#             categories = [f["category"] for f in failed_tests]
#             if categories.count("Navigation") > 2:
#                 log("  INSIGHT: Multiple navigation failures — possible app issue")
#                 self.memory.learn_skill("navigation_issue", {
#                     "pattern": "multiple_nav_failures",
#                     "suggestion": "check if app is responsive"
#                 })

#             if categories.count("Button") > 2:
#                 log("  INSIGHT: Multiple button failures — possible JS loading issue")
#                 self.memory.learn_skill("button_issue", {
#                     "pattern": "multiple_button_failures",
#                     "suggestion": "increase wait times"
#                 })
#         else:
#             log("No failures to analyze — all tests passed!")

#         log(f"Agent has {len(self.memory.data['learned_skills'])} skills in memory")

#     # ====================================
#     # REPORT — Generate final output
#     # ====================================

#     def _generate_report(self):
#         """Generate comprehensive test report"""
#         summary = self.memory.get_summary()

#         log("=" * 60)
#         log("FINAL AGENT REPORT")
#         log("=" * 60)
#         log(f"Session: #{summary['session']}")
#         log(f"Total Tests: {summary['total_tests']}")
#         log(f"Passed: {summary['passed']}")
#         log(f"Failed: {summary['failed']}")
#         log(f"Skipped: {summary['skipped']}")
#         log(f"Pass Rate: {summary['pass_rate']}")
#         log(f"Skills Learned: {summary['skills_learned']}")
#         log(f"Known Selectors: {summary['known_selectors']}")
#         log("=" * 60)

#         # Category breakdown
#         categories = {}
#         for r in self.test_results:
#             cat = r["category"]
#             if cat not in categories:
#                 categories[cat] = {"pass": 0, "fail": 0, "skip": 0}
#             categories[cat][r["status"].lower()] = categories[cat].get(r["status"].lower(), 0) + 1

#         log("\nCategory Breakdown:")
#         for cat, counts in categories.items():
#             log(f"  {cat}: PASS={counts.get('pass',0)} FAIL={counts.get('fail',0)} SKIP={counts.get('skip',0)}")

#         # Failed tests detail
#         failed = [r for r in self.test_results if r["status"] == "FAIL"]
#         if failed:
#             log(f"\nFailed Tests ({len(failed)}):")
#             for f in failed:
#                 log(f"  [{f['id']}] {f['name']}")
#                 log(f"    Reason: {f['details']}")

#         # Save report as JSON
#         report = {
#             "summary": summary,
#             "categories": categories,
#             "all_results": self.test_results,
#             "failed_details": failed,
#             "memory_snapshot": {
#                 "skills": len(self.memory.data["learned_skills"]),
#                 "known_pages": len(self.memory.data["known_pages"]),
#             }
#         }

#         os.makedirs(config.REPORT_DIR, exist_ok=True)
#         with open(f"{config.REPORT_DIR}/test_report.json", "w") as f:
#             json.dump(report, f, indent=2)
#         log(f"\nReport saved to {config.REPORT_DIR}/test_report.json")

#         return report