from utils.logger import log
from urllib.parse import urlparse
import config
import os


class Executor:
    def __init__(self, page, url=None, username=None, password=None):
        self.page = page
        self.app_url = url or config.APP_URL
        self.username = username or config.USERNAME
        self.password = password or config.PASSWORD
        self.allowed_domain = urlparse(self.app_url).netloc
        self.console_errors = []
        self.last_used_selector = {}
        self.page.on("console", self._capture_console)

    def _capture_console(self, msg):
        if msg.type == "error":
            self.console_errors.append(msg.text)

    def navigate(self, url):
        log(f"Navigating to: {url}")
        self.page.goto(url, wait_until="networkidle")
        log(f"Loaded: {self.page.title()}")

    def find_and_fill(self, selectors, value, field_name):
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=3000):
                    element.fill(value)
                    log(f"Filled '{field_name}' using selector: {selector}")
                    self.last_used_selector[field_name] = selector
                    return True
            except Exception:
                continue
        log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
        return False

    def find_and_click(self, selectors, button_name):
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=3000):
                    element.click()
                    log(f"Clicked '{button_name}' using selector: {selector}")
                    self.last_used_selector[button_name] = selector
                    return True
            except Exception:
                continue
        log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
        return False

    def login(self):
        log("=" * 50)
        log("LOGIN PHASE STARTED")
        log("=" * 50)

        self.navigate(self.app_url)
        self.take_screenshot("01_login_page")
        login_url = self.page.url

        username_ok = self.find_and_fill(
            config.LOGIN_SELECTORS["username"],
            self.username,
            "username"
        )

        password_ok = self.find_and_fill(
            config.LOGIN_SELECTORS["password"],
            self.password,
            "password"
        )

        if not username_ok or not password_ok:
            log("Login aborted: could not find input fields", level="ERROR")
            self.take_screenshot("login_field_error")
            return False

        submit_ok = self.find_and_click(
            config.LOGIN_SELECTORS["submit"],
            "submit"
        )

        if not submit_ok:
            log("Login aborted: could not find submit button", level="ERROR")
            self.take_screenshot("login_button_error")
            return False

        log("Waiting for redirect after login...")

        try:
            self.page.wait_for_url(
                lambda url: url != login_url,
                timeout=15000
            )
            log(f"URL changed to: {self.page.url}")
        except Exception:
            log("URL did not change — trying alternative waits", level="WARN")

        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            log("Network idle timeout", level="WARN")

        try:
            self.page.wait_for_timeout(3000)
        except Exception:
            pass

        log(f"Final URL after login: {self.page.url}")
        self.take_screenshot("02_after_login")
        return True

    def take_screenshot(self, name):
        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
        path = f"{config.SCREENSHOT_DIR}/{name}.png"
        self.page.screenshot(path=path)
        log(f"Screenshot saved: {name}.png")

    def get_current_url(self):
        return self.page.url

    def get_page_title(self):
        return self.page.title()

    def run_test(self, test_case):
        test_type = test_case["type"]
        try:
            if test_type == "page_load":
                return self._test_page_load(test_case)
            elif test_type == "login":
                return self._test_login(test_case)
            elif test_type == "element_exists":
                return self._test_element_exists(test_case)
            elif test_type == "title_check":
                return self._test_title(test_case)
            elif test_type == "console_check":
                return self._test_console(test_case)
            elif test_type == "button_click":
                return self._test_button_click(test_case)
            elif test_type == "input_fill":
                return self._test_input_fill(test_case)
            elif test_type == "table_check":
                return self._test_table(test_case)
            elif test_type == "cross_navigation":
                return self._test_cross_nav(test_case)
            elif test_type == "not_blank":
                return self._test_not_blank(test_case)
            elif test_type == "logout":
                return self._test_logout(test_case)
            elif test_type == "search_workflow":
                return self._test_search_workflow(test_case)
            elif test_type == "sort_workflow":
                return self._test_sort_workflow(test_case)
            elif test_type == "filter_workflow":
                return self._test_filter_workflow(test_case)
            elif test_type == "form_workflow":
                return self._test_form_workflow(test_case)
            elif test_type == "error_handling":
                return self._test_error_handling(test_case)
            elif test_type == "back_navigation":
                return self._test_back_navigation(test_case)
            elif test_type == "reload_test":
                return self._test_reload(test_case)
            else:
                return {"status": "SKIP", "details": f"Unknown test type: {test_type}"}
        except Exception as e:
            return {"status": "FAIL", "details": f"Exception: {str(e)[:200]}"}

    def _test_page_load(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        current = self.page.url
        title = self.page.title()
        if title and len(self.page.content()) > 100:
            return {"status": "PASS", "details": f"Page loaded: {title}"}
        return {"status": "FAIL", "details": f"Page may not have loaded properly at {current}"}

    def _test_login(self, tc):
        current = self.page.url.lower()
        if "dashboard" in current or "app" in current:
            return {"status": "PASS", "details": f"Logged in at: {self.page.url}"}
        return {"status": "FAIL", "details": f"Not on dashboard: {self.page.url}"}

    def _test_element_exists(self, tc):
        url = tc.get("target_url", "")
        if url:
            self.page.goto(url, wait_until="networkidle", timeout=15000)
        selectors = tc["selector"]
        for sel in selectors:
            try:
                element = self.page.locator(sel).first
                if element.is_visible(timeout=3000):
                    return {"status": "PASS", "details": f"Found element: {sel}"}
            except Exception:
                continue
        return {"status": "FAIL", "details": "Element not found with any selector"}

    def _test_title(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        title = self.page.title()
        if title and len(title.strip()) > 0:
            return {"status": "PASS", "details": f"Title: {title}"}
        return {"status": "FAIL", "details": "Page has no title"}

    def _test_console(self, tc):
        url = tc["target_url"]
        self.console_errors = []
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        self.page.wait_for_timeout(2000)
        if len(self.console_errors) == 0:
            return {"status": "PASS", "details": "No console errors"}
        return {
            "status": "FAIL",
            "details": f"{len(self.console_errors)} console errors: {self.console_errors[:3]}"
        }

    def _test_button_click(self, tc):
        url = tc["target_url"]
        btn_text = tc["button_text"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        try:
            btn = self.page.locator(f'button:has-text("{btn_text}")').first
            if btn.is_visible(timeout=3000):
                btn.click()
                self.page.wait_for_timeout(1000)
                return {"status": "PASS", "details": f"Clicked '{btn_text}' successfully"}
        except Exception as e:
            return {"status": "FAIL", "details": f"Could not click '{btn_text}': {str(e)[:100]}"}
        return {"status": "FAIL", "details": f"Button '{btn_text}' not visible"}

    def _test_input_fill(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        try:
            inputs = self.page.locator("input:visible").all()
            if inputs:
                first_input = inputs[0]
                first_input.fill("test_input_123")
                self.page.wait_for_timeout(500)
                value = first_input.input_value()
                if "test_input_123" in value:
                    first_input.fill("")
                    return {"status": "PASS", "details": "Input accepted text"}
                return {"status": "FAIL", "details": "Input did not retain value"}
            return {"status": "FAIL", "details": "No visible inputs found"}
        except Exception as e:
            return {"status": "FAIL", "details": f"Input error: {str(e)[:100]}"}

    def _test_table(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        try:
            rows = self.page.locator("table tbody tr").count()
            if rows > 0:
                return {"status": "PASS", "details": f"Table has {rows} rows"}
            return {"status": "FAIL", "details": "Table has no rows"}
        except Exception:
            return {"status": "FAIL", "details": "Could not find table rows"}

    def _test_cross_nav(self, tc):
        from_url = tc["from_url"]
        to_url = tc["to_url"]
        to_name = tc["to_name"]
        self.page.goto(from_url, wait_until="networkidle", timeout=15000)
        try:
            link = self.page.locator(f'a:has-text("{to_name}")').first
            if link.is_visible(timeout=3000):
                link.click()
                self.page.wait_for_load_state("networkidle", timeout=10000)
                current = self.page.url
                if to_name.lower() in current.lower() or current == to_url:
                    return {"status": "PASS", "details": f"Navigated to {current}"}
                return {"status": "FAIL", "details": f"Expected {to_url}, got {current}"}
        except Exception as e:
            return {"status": "FAIL", "details": f"Nav failed: {str(e)[:100]}"}
        return {"status": "FAIL", "details": f"Link to '{to_name}' not found"}

    def _test_not_blank(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)
        content = self.page.content()
        body_text = self.page.locator("body").inner_text()
        if len(body_text.strip()) > 10:
            return {"status": "PASS", "details": f"Page has content ({len(body_text)} chars)"}
        return {"status": "FAIL", "details": "Page appears blank"}

    def _test_logout(self, tc):
        try:
            base_path = "/".join(urlparse(self.app_url).path.split("/")[:-1])

            for kw in ["profile", "settings", "account"]:
                candidate = f"https://{self.allowed_domain}{base_path}/{kw}"
                try:
                    self.page.goto(candidate, wait_until="networkidle", timeout=10000)
                    break
                except Exception:
                    continue

            logout_selectors = [
                'button:has-text("Logout")',
                'button:has-text("Log out")',
                'a:has-text("Logout")',
                'a:has-text("Log out")',
            ]

            for sel in logout_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        self.page.wait_for_timeout(3000)
                        current = self.page.url.lower()
                        if "login" in current:
                            return {"status": "PASS", "details": "Logged out successfully"}
                        return {"status": "PASS", "details": f"Logout clicked, at: {self.page.url}"}
                except Exception:
                    continue

            return {"status": "FAIL", "details": "Logout button not found"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Logout error: {str(e)[:100]}"}

    # =============================================
    # Deep Functional Test Methods
    # =============================================

    def _test_search_workflow(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            before_content = self.page.locator("body").inner_text()

            search_input = None
            for sel in ['input[type="search"]', 'input[placeholder*="search" i]',
                        'input[placeholder*="find" i]', 'input:visible']:
                try:
                    inp = self.page.locator(sel).first
                    if inp.is_visible(timeout=2000):
                        search_input = inp
                        break
                except Exception:
                    continue

            if not search_input:
                return {"status": "SKIP", "details": "No search input found"}

            search_input.fill("test")
            self.page.wait_for_timeout(2000)

            try:
                search_input.press("Enter")
            except Exception:
                pass
            self.page.wait_for_timeout(2000)

            after_content = self.page.locator("body").inner_text()

            search_input.fill("")
            try:
                search_input.press("Enter")
            except Exception:
                pass
            self.page.wait_for_timeout(1000)

            if before_content != after_content:
                return {"status": "PASS", "details": "Search changed page content"}
            return {"status": "PASS", "details": "Search executed (content may not have changed for test term)"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Search workflow error: {str(e)[:100]}"}

    def _test_sort_workflow(self, tc):
        url = tc["target_url"]
        btn_text = tc["button_text"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            before_content = self.page.locator("body").inner_text()

            btn = self.page.locator(f'button:has-text("{btn_text}")').first
            if not btn.is_visible(timeout=3000):
                return {"status": "FAIL", "details": f"Sort button '{btn_text}' not visible"}

            btn.click()
            self.page.wait_for_timeout(2000)

            after_content = self.page.locator("body").inner_text()

            if before_content != after_content:
                return {"status": "PASS", "details": f"Sort '{btn_text}' changed page content"}
            return {"status": "PASS", "details": f"Sort '{btn_text}' clicked (content stable)"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Sort workflow error: {str(e)[:100]}"}

    def _test_filter_workflow(self, tc):
        url = tc["target_url"]
        btn_text = tc["button_text"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            before_content = self.page.locator("body").inner_text()

            btn = self.page.locator(f'button:has-text("{btn_text}")').first
            if not btn.is_visible(timeout=3000):
                return {"status": "FAIL", "details": f"Filter button '{btn_text}' not visible"}

            btn.click()
            self.page.wait_for_timeout(2000)

            after_content = self.page.locator("body").inner_text()

            if len(after_content) > 0:
                change = "content changed" if before_content != after_content else "content stable"
                return {"status": "PASS", "details": f"Filter '{btn_text}' applied ({change})"}
            return {"status": "FAIL", "details": f"Page went blank after filter '{btn_text}'"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Filter workflow error: {str(e)[:100]}"}

    def _test_form_workflow(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            inputs = self.page.locator("input:visible").all()
            filled_count = 0

            for inp in inputs:
                try:
                    inp_type = inp.get_attribute("type") or "text"

                    if inp_type in ["hidden", "submit", "file", "checkbox", "radio", "button"]:
                        continue

                    if inp_type == "email":
                        inp.fill("test@example.com")
                    elif inp_type == "number":
                        inp.fill("123")
                    elif inp_type == "tel":
                        inp.fill("1234567890")
                    elif inp_type == "date":
                        inp.fill("2026-01-01")
                    else:
                        inp.fill("test_data")

                    filled_count += 1
                except Exception:
                    continue

            if filled_count == 0:
                return {"status": "SKIP", "details": "No fillable inputs found"}

            submitted = False
            for sel in ['button[type="submit"]', 'input[type="submit"]',
                        'button:has-text("Submit")', 'button:has-text("Save")',
                        'button:has-text("Apply")', 'button:has-text("Create")']:
                try:
                    btn = self.page.locator(sel).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            self.page.wait_for_timeout(2000)

            body = self.page.locator("body").inner_text()
            if len(body) > 0:
                if submitted:
                    return {"status": "PASS", "details": f"Form filled ({filled_count} fields) and submitted"}
                return {"status": "PASS", "details": f"Form filled ({filled_count} fields), no submit button found"}
            return {"status": "FAIL", "details": "Page blank after form interaction"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Form workflow error: {str(e)[:100]}"}

    def _test_error_handling(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            self.console_errors = []

            try:
                self.page.locator("body").click()
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            try:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            try:
                for _ in range(3):
                    self.page.keyboard.press("Tab")
                    self.page.wait_for_timeout(200)
            except Exception:
                pass

            body = self.page.locator("body").inner_text()
            if len(body.strip()) > 10:
                errors = len(self.console_errors)
                if errors == 0:
                    return {"status": "PASS", "details": "Page handles empty interactions gracefully"}
                return {"status": "PASS", "details": f"Page stable but {errors} console errors detected"}
            return {"status": "FAIL", "details": "Page crashed after empty interactions"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Error handling test failed: {str(e)[:100]}"}

    def _test_back_navigation(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            base_path = "/".join(urlparse(self.app_url).path.split("/")[:-1])
            dashboard_url = f"https://{self.allowed_domain}{base_path}/app/dashboard"
            self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)

            self.page.goto(url, wait_until="networkidle", timeout=15000)

            self.page.go_back()
            self.page.wait_for_timeout(2000)

            back_url = self.page.url
            body = self.page.locator("body").inner_text()

            if len(body.strip()) > 10:
                return {"status": "PASS", "details": f"Back navigation works (went to {back_url})"}
            return {"status": "FAIL", "details": "Page blank after back navigation"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Back nav error: {str(e)[:100]}"}

    def _test_reload(self, tc):
        url = tc["target_url"]
        self.page.goto(url, wait_until="networkidle", timeout=15000)

        try:
            before_title = self.page.title()

            self.page.reload(wait_until="networkidle", timeout=15000)
            self.page.wait_for_timeout(2000)

            after_title = self.page.title()
            body = self.page.locator("body").inner_text()

            if len(body.strip()) > 10:
                if "login" in self.page.url.lower():
                    return {"status": "FAIL", "details": "Reload redirected to login (session lost)"}
                return {"status": "PASS", "details": f"Page survives reload (title: {after_title})"}
            return {"status": "FAIL", "details": "Page blank after reload"}

        except Exception as e:
            return {"status": "FAIL", "details": f"Reload test error: {str(e)[:100]}"}







# from utils.logger import log
# import config
# import os


# class Executor:
#     def __init__(self, page):
#         self.page = page
#         self.console_errors = []
#         self.last_used_selector = {}
#         self.page.on("console", self._capture_console)

#     def _capture_console(self, msg):
#         if msg.type == "error":
#             self.console_errors.append(msg.text)

#     def navigate(self, url):
#         log(f"Navigating to: {url}")
#         self.page.goto(url, wait_until="networkidle")
#         log(f"Loaded: {self.page.title()}")

#     def find_and_fill(self, selectors, value, field_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.fill(value)
#                     log(f"Filled '{field_name}' using selector: {selector}")
#                     self.last_used_selector[field_name] = selector
#                     return True
#             except Exception:
#                 continue
#         log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
#         return False

#     def find_and_click(self, selectors, button_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.click()
#                     log(f"Clicked '{button_name}' using selector: {selector}")
#                     self.last_used_selector[button_name] = selector
#                     return True
#             except Exception:
#                 continue
#         log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
#         return False

#     def login(self):
#         log("=" * 50)
#         log("LOGIN PHASE STARTED")
#         log("=" * 50)

#         self.navigate(config.APP_URL)
#         self.take_screenshot("01_login_page")
#         login_url = self.page.url

#         username_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["username"],
#             config.USERNAME,
#             "username"
#         )

#         password_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["password"],
#             config.PASSWORD,
#             "password"
#         )

#         if not username_ok or not password_ok:
#             log("Login aborted: could not find input fields", level="ERROR")
#             self.take_screenshot("login_field_error")
#             return False

#         submit_ok = self.find_and_click(
#             config.LOGIN_SELECTORS["submit"],
#             "submit"
#         )

#         if not submit_ok:
#             log("Login aborted: could not find submit button", level="ERROR")
#             self.take_screenshot("login_button_error")
#             return False

#         log("Waiting for redirect after login...")

#         try:
#             self.page.wait_for_url(
#                 lambda url: url != login_url,
#                 timeout=15000
#             )
#             log(f"URL changed to: {self.page.url}")
#         except Exception:
#             log("URL did not change — trying alternative waits", level="WARN")

#         try:
#             self.page.wait_for_load_state("networkidle", timeout=10000)
#         except Exception:
#             log("Network idle timeout", level="WARN")

#         try:
#             self.page.wait_for_timeout(3000)
#         except Exception:
#             pass

#         log(f"Final URL after login: {self.page.url}")
#         self.take_screenshot("02_after_login")
#         return True

#     def take_screenshot(self, name):
#         os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
#         path = f"{config.SCREENSHOT_DIR}/{name}.png"
#         self.page.screenshot(path=path)
#         log(f"Screenshot saved: {name}.png")

#     def get_current_url(self):
#         return self.page.url

#     def get_page_title(self):
#         return self.page.title()

#     def run_test(self, test_case):
#         test_type = test_case["type"]
#         try:
#             if test_type == "page_load":
#                 return self._test_page_load(test_case)
#             elif test_type == "login":
#                 return self._test_login(test_case)
#             elif test_type == "element_exists":
#                 return self._test_element_exists(test_case)
#             elif test_type == "title_check":
#                 return self._test_title(test_case)
#             elif test_type == "console_check":
#                 return self._test_console(test_case)
#             elif test_type == "button_click":
#                 return self._test_button_click(test_case)
#             elif test_type == "input_fill":
#                 return self._test_input_fill(test_case)
#             elif test_type == "table_check":
#                 return self._test_table(test_case)
#             elif test_type == "cross_navigation":
#                 return self._test_cross_nav(test_case)
#             elif test_type == "not_blank":
#                 return self._test_not_blank(test_case)
#             elif test_type == "logout":
#                 return self._test_logout(test_case)
#             elif test_type == "search_workflow":
#                 return self._test_search_workflow(test_case)
#             elif test_type == "sort_workflow":
#                 return self._test_sort_workflow(test_case)
#             elif test_type == "filter_workflow":
#                 return self._test_filter_workflow(test_case)
#             elif test_type == "form_workflow":
#                 return self._test_form_workflow(test_case)
#             elif test_type == "error_handling":
#                 return self._test_error_handling(test_case)
#             elif test_type == "back_navigation":
#                 return self._test_back_navigation(test_case)
#             elif test_type == "reload_test":
#                 return self._test_reload(test_case)
#             else:
#                 return {"status": "SKIP", "details": f"Unknown test type: {test_type}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Exception: {str(e)[:200]}"}

#     def _test_page_load(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         current = self.page.url
#         title = self.page.title()
#         if title and len(self.page.content()) > 100:
#             return {"status": "PASS", "details": f"Page loaded: {title}"}
#         return {"status": "FAIL", "details": f"Page may not have loaded properly at {current}"}

#     def _test_login(self, tc):
#         current = self.page.url.lower()
#         if "dashboard" in current or "app" in current:
#             return {"status": "PASS", "details": f"Logged in at: {self.page.url}"}
#         return {"status": "FAIL", "details": f"Not on dashboard: {self.page.url}"}

#     def _test_element_exists(self, tc):
#         url = tc.get("target_url", "")
#         if url:
#             self.page.goto(url, wait_until="networkidle", timeout=15000)
#         selectors = tc["selector"]
#         for sel in selectors:
#             try:
#                 element = self.page.locator(sel).first
#                 if element.is_visible(timeout=3000):
#                     return {"status": "PASS", "details": f"Found element: {sel}"}
#             except Exception:
#                 continue
#         return {"status": "FAIL", "details": "Element not found with any selector"}

#     def _test_title(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         title = self.page.title()
#         if title and len(title.strip()) > 0:
#             return {"status": "PASS", "details": f"Title: {title}"}
#         return {"status": "FAIL", "details": "Page has no title"}

#     def _test_console(self, tc):
#         url = tc["target_url"]
#         self.console_errors = []
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         self.page.wait_for_timeout(2000)
#         if len(self.console_errors) == 0:
#             return {"status": "PASS", "details": "No console errors"}
#         return {
#             "status": "FAIL",
#             "details": f"{len(self.console_errors)} console errors: {self.console_errors[:3]}"
#         }

#     def _test_button_click(self, tc):
#         url = tc["target_url"]
#         btn_text = tc["button_text"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             btn = self.page.locator(f'button:has-text("{btn_text}")').first
#             if btn.is_visible(timeout=3000):
#                 btn.click()
#                 self.page.wait_for_timeout(1000)
#                 return {"status": "PASS", "details": f"Clicked '{btn_text}' successfully"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Could not click '{btn_text}': {str(e)[:100]}"}
#         return {"status": "FAIL", "details": f"Button '{btn_text}' not visible"}

#     def _test_input_fill(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             inputs = self.page.locator("input:visible").all()
#             if inputs:
#                 first_input = inputs[0]
#                 first_input.fill("test_input_123")
#                 self.page.wait_for_timeout(500)
#                 value = first_input.input_value()
#                 if "test_input_123" in value:
#                     first_input.fill("")
#                     return {"status": "PASS", "details": "Input accepted text"}
#                 return {"status": "FAIL", "details": "Input did not retain value"}
#             return {"status": "FAIL", "details": "No visible inputs found"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Input error: {str(e)[:100]}"}

#     def _test_table(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             rows = self.page.locator("table tbody tr").count()
#             if rows > 0:
#                 return {"status": "PASS", "details": f"Table has {rows} rows"}
#             return {"status": "FAIL", "details": "Table has no rows"}
#         except Exception:
#             return {"status": "FAIL", "details": "Could not find table rows"}

#     def _test_cross_nav(self, tc):
#         from_url = tc["from_url"]
#         to_url = tc["to_url"]
#         to_name = tc["to_name"]
#         self.page.goto(from_url, wait_until="networkidle", timeout=15000)
#         try:
#             link = self.page.locator(f'a:has-text("{to_name}")').first
#             if link.is_visible(timeout=3000):
#                 link.click()
#                 self.page.wait_for_load_state("networkidle", timeout=10000)
#                 current = self.page.url
#                 if to_name.lower() in current.lower() or current == to_url:
#                     return {"status": "PASS", "details": f"Navigated to {current}"}
#                 return {"status": "FAIL", "details": f"Expected {to_url}, got {current}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Nav failed: {str(e)[:100]}"}
#         return {"status": "FAIL", "details": f"Link to '{to_name}' not found"}

#     def _test_not_blank(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         content = self.page.content()
#         body_text = self.page.locator("body").inner_text()
#         if len(body_text.strip()) > 10:
#             return {"status": "PASS", "details": f"Page has content ({len(body_text)} chars)"}
#         return {"status": "FAIL", "details": "Page appears blank"}

#     def _test_logout(self, tc):
#         try:
#             for kw in ["profile", "settings", "account"]:
#                 candidate = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/{kw}"
#                 try:
#                     self.page.goto(candidate, wait_until="networkidle", timeout=10000)
#                     break
#                 except Exception:
#                     continue

#             logout_selectors = [
#                 'button:has-text("Logout")',
#                 'button:has-text("Log out")',
#                 'a:has-text("Logout")',
#                 'a:has-text("Log out")',
#             ]

#             for sel in logout_selectors:
#                 try:
#                     btn = self.page.locator(sel).first
#                     if btn.is_visible(timeout=3000):
#                         btn.click()
#                         self.page.wait_for_timeout(3000)
#                         current = self.page.url.lower()
#                         if "login" in current:
#                             return {"status": "PASS", "details": "Logged out successfully"}
#                         return {"status": "PASS", "details": f"Logout clicked, at: {self.page.url}"}
#                 except Exception:
#                     continue

#             return {"status": "FAIL", "details": "Logout button not found"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Logout error: {str(e)[:100]}"}

#     # =============================================
#     # Deep Functional Test Methods (Upgrade 3)
#     # =============================================

#     def _test_search_workflow(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             before_content = self.page.locator("body").inner_text()

#             search_input = None
#             for sel in ['input[type="search"]', 'input[placeholder*="search" i]',
#                         'input[placeholder*="find" i]', 'input:visible']:
#                 try:
#                     inp = self.page.locator(sel).first
#                     if inp.is_visible(timeout=2000):
#                         search_input = inp
#                         break
#                 except Exception:
#                     continue

#             if not search_input:
#                 return {"status": "SKIP", "details": "No search input found"}

#             search_input.fill("test")
#             self.page.wait_for_timeout(2000)

#             try:
#                 search_input.press("Enter")
#             except Exception:
#                 pass
#             self.page.wait_for_timeout(2000)

#             after_content = self.page.locator("body").inner_text()

#             search_input.fill("")
#             try:
#                 search_input.press("Enter")
#             except Exception:
#                 pass
#             self.page.wait_for_timeout(1000)

#             if before_content != after_content:
#                 return {"status": "PASS", "details": "Search changed page content"}
#             return {"status": "PASS", "details": "Search executed (content may not have changed for test term)"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Search workflow error: {str(e)[:100]}"}

#     def _test_sort_workflow(self, tc):
#         url = tc["target_url"]
#         btn_text = tc["button_text"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             before_content = self.page.locator("body").inner_text()

#             btn = self.page.locator(f'button:has-text("{btn_text}")').first
#             if not btn.is_visible(timeout=3000):
#                 return {"status": "FAIL", "details": f"Sort button '{btn_text}' not visible"}

#             btn.click()
#             self.page.wait_for_timeout(2000)

#             after_content = self.page.locator("body").inner_text()

#             if before_content != after_content:
#                 return {"status": "PASS", "details": f"Sort '{btn_text}' changed page content"}
#             return {"status": "PASS", "details": f"Sort '{btn_text}' clicked (content stable)"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Sort workflow error: {str(e)[:100]}"}

#     def _test_filter_workflow(self, tc):
#         url = tc["target_url"]
#         btn_text = tc["button_text"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             before_content = self.page.locator("body").inner_text()

#             btn = self.page.locator(f'button:has-text("{btn_text}")').first
#             if not btn.is_visible(timeout=3000):
#                 return {"status": "FAIL", "details": f"Filter button '{btn_text}' not visible"}

#             btn.click()
#             self.page.wait_for_timeout(2000)

#             after_content = self.page.locator("body").inner_text()

#             if len(after_content) > 0:
#                 change = "content changed" if before_content != after_content else "content stable"
#                 return {"status": "PASS", "details": f"Filter '{btn_text}' applied ({change})"}
#             return {"status": "FAIL", "details": f"Page went blank after filter '{btn_text}'"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Filter workflow error: {str(e)[:100]}"}

#     def _test_form_workflow(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             inputs = self.page.locator("input:visible").all()
#             filled_count = 0

#             for inp in inputs:
#                 try:
#                     inp_type = inp.get_attribute("type") or "text"

#                     if inp_type in ["hidden", "submit", "file", "checkbox", "radio", "button"]:
#                         continue

#                     if inp_type == "email":
#                         inp.fill("test@example.com")
#                     elif inp_type == "number":
#                         inp.fill("123")
#                     elif inp_type == "tel":
#                         inp.fill("1234567890")
#                     elif inp_type == "date":
#                         inp.fill("2026-01-01")
#                     else:
#                         inp.fill("test_data")

#                     filled_count += 1
#                 except Exception:
#                     continue

#             if filled_count == 0:
#                 return {"status": "SKIP", "details": "No fillable inputs found"}

#             submitted = False
#             for sel in ['button[type="submit"]', 'input[type="submit"]',
#                         'button:has-text("Submit")', 'button:has-text("Save")',
#                         'button:has-text("Apply")', 'button:has-text("Create")']:
#                 try:
#                     btn = self.page.locator(sel).first
#                     if btn.is_visible(timeout=2000):
#                         btn.click()
#                         submitted = True
#                         break
#                 except Exception:
#                     continue

#             self.page.wait_for_timeout(2000)

#             body = self.page.locator("body").inner_text()
#             if len(body) > 0:
#                 if submitted:
#                     return {"status": "PASS", "details": f"Form filled ({filled_count} fields) and submitted"}
#                 return {"status": "PASS", "details": f"Form filled ({filled_count} fields), no submit button found"}
#             return {"status": "FAIL", "details": "Page blank after form interaction"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Form workflow error: {str(e)[:100]}"}

#     def _test_error_handling(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             self.console_errors = []

#             try:
#                 self.page.locator("body").click()
#                 self.page.wait_for_timeout(500)
#             except Exception:
#                 pass

#             try:
#                 self.page.keyboard.press("Escape")
#                 self.page.wait_for_timeout(500)
#             except Exception:
#                 pass

#             try:
#                 for _ in range(3):
#                     self.page.keyboard.press("Tab")
#                     self.page.wait_for_timeout(200)
#             except Exception:
#                 pass

#             body = self.page.locator("body").inner_text()
#             if len(body.strip()) > 10:
#                 errors = len(self.console_errors)
#                 if errors == 0:
#                     return {"status": "PASS", "details": "Page handles empty interactions gracefully"}
#                 return {"status": "PASS", "details": f"Page stable but {errors} console errors detected"}
#             return {"status": "FAIL", "details": "Page crashed after empty interactions"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Error handling test failed: {str(e)[:100]}"}

#     def _test_back_navigation(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             dashboard_url = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/dashboard"
#             self.page.goto(dashboard_url, wait_until="networkidle", timeout=10000)

#             self.page.goto(url, wait_until="networkidle", timeout=15000)

#             self.page.go_back()
#             self.page.wait_for_timeout(2000)

#             back_url = self.page.url
#             body = self.page.locator("body").inner_text()

#             if len(body.strip()) > 10:
#                 return {"status": "PASS", "details": f"Back navigation works (went to {back_url})"}
#             return {"status": "FAIL", "details": "Page blank after back navigation"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Back nav error: {str(e)[:100]}"}

#     def _test_reload(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             before_title = self.page.title()

#             self.page.reload(wait_until="networkidle", timeout=15000)
#             self.page.wait_for_timeout(2000)

#             after_title = self.page.title()
#             body = self.page.locator("body").inner_text()

#             if len(body.strip()) > 10:
#                 if "login" in self.page.url.lower():
#                     return {"status": "FAIL", "details": "Reload redirected to login (session lost)"}
#                 return {"status": "PASS", "details": f"Page survives reload (title: {after_title})"}
#             return {"status": "FAIL", "details": "Page blank after reload"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Reload test error: {str(e)[:100]}"}







# from utils.logger import log
# import config
# import os


# class Executor:
#     def __init__(self, page):
#         self.page = page
#         self.console_errors = []
#         self.last_used_selector = {}
#         self.page.on("console", self._capture_console)

#     def _capture_console(self, msg):
#         if msg.type == "error":
#             self.console_errors.append(msg.text)

#     def navigate(self, url):
#         log(f"Navigating to: {url}")
#         self.page.goto(url, wait_until="networkidle")
#         log(f"Loaded: {self.page.title()}")

#     def find_and_fill(self, selectors, value, field_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.fill(value)
#                     log(f"Filled '{field_name}' using selector: {selector}")
#                     self.last_used_selector[field_name] = selector
#                     return True
#             except Exception:
#                 continue
#         log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
#         return False

#     def find_and_click(self, selectors, button_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.click()
#                     log(f"Clicked '{button_name}' using selector: {selector}")
#                     self.last_used_selector[button_name] = selector
#                     return True
#             except Exception:
#                 continue
#         log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
#         return False

#     def login(self):
#         log("=" * 50)
#         log("LOGIN PHASE STARTED")
#         log("=" * 50)

#         self.navigate(config.APP_URL)
#         self.take_screenshot("01_login_page")
#         login_url = self.page.url

#         username_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["username"],
#             config.USERNAME,
#             "username"
#         )

#         password_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["password"],
#             config.PASSWORD,
#             "password"
#         )

#         if not username_ok or not password_ok:
#             log("Login aborted: could not find input fields", level="ERROR")
#             self.take_screenshot("login_field_error")
#             return False

#         submit_ok = self.find_and_click(
#             config.LOGIN_SELECTORS["submit"],
#             "submit"
#         )

#         if not submit_ok:
#             log("Login aborted: could not find submit button", level="ERROR")
#             self.take_screenshot("login_button_error")
#             return False

#         log("Waiting for redirect after login...")

#         try:
#             self.page.wait_for_url(
#                 lambda url: url != login_url,
#                 timeout=15000
#             )
#             log(f"URL changed to: {self.page.url}")
#         except Exception:
#             log("URL did not change — trying alternative waits", level="WARN")

#         try:
#             self.page.wait_for_load_state("networkidle", timeout=10000)
#         except Exception:
#             log("Network idle timeout", level="WARN")

#         try:
#             self.page.wait_for_timeout(3000)
#         except Exception:
#             pass

#         log(f"Final URL after login: {self.page.url}")
#         self.take_screenshot("02_after_login")
#         return True

#     def take_screenshot(self, name):
#         os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
#         path = f"{config.SCREENSHOT_DIR}/{name}.png"
#         self.page.screenshot(path=path)
#         log(f"Screenshot saved: {name}.png")

#     def get_current_url(self):
#         return self.page.url

#     def get_page_title(self):
#         return self.page.title()

#     def run_test(self, test_case):
#         test_type = test_case["type"]
#         try:
#             if test_type == "page_load":
#                 return self._test_page_load(test_case)
#             elif test_type == "login":
#                 return self._test_login(test_case)
#             elif test_type == "element_exists":
#                 return self._test_element_exists(test_case)
#             elif test_type == "title_check":
#                 return self._test_title(test_case)
#             elif test_type == "console_check":
#                 return self._test_console(test_case)
#             elif test_type == "button_click":
#                 return self._test_button_click(test_case)
#             elif test_type == "input_fill":
#                 return self._test_input_fill(test_case)
#             elif test_type == "table_check":
#                 return self._test_table(test_case)
#             elif test_type == "cross_navigation":
#                 return self._test_cross_nav(test_case)
#             elif test_type == "not_blank":
#                 return self._test_not_blank(test_case)
#             elif test_type == "logout":
#                 return self._test_logout(test_case)
#             else:
#                 return {"status": "SKIP", "details": f"Unknown test type: {test_type}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Exception: {str(e)[:200]}"}

#     def _test_page_load(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         current = self.page.url
#         title = self.page.title()
#         if title and len(self.page.content()) > 100:
#             return {"status": "PASS", "details": f"Page loaded: {title}"}
#         return {"status": "FAIL", "details": f"Page may not have loaded properly at {current}"}

#     def _test_login(self, tc):
#         current = self.page.url.lower()
#         if "dashboard" in current or "app" in current:
#             return {"status": "PASS", "details": f"Logged in at: {self.page.url}"}
#         return {"status": "FAIL", "details": f"Not on dashboard: {self.page.url}"}

#     def _test_element_exists(self, tc):
#         url = tc.get("target_url", "")
#         if url:
#             self.page.goto(url, wait_until="networkidle", timeout=15000)
#         selectors = tc["selector"]
#         for sel in selectors:
#             try:
#                 element = self.page.locator(sel).first
#                 if element.is_visible(timeout=3000):
#                     return {"status": "PASS", "details": f"Found element: {sel}"}
#             except Exception:
#                 continue
#         return {"status": "FAIL", "details": "Element not found with any selector"}

#     def _test_title(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         title = self.page.title()
#         if title and len(title.strip()) > 0:
#             return {"status": "PASS", "details": f"Title: {title}"}
#         return {"status": "FAIL", "details": "Page has no title"}

#     def _test_console(self, tc):
#         url = tc["target_url"]
#         self.console_errors = []
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         self.page.wait_for_timeout(2000)
#         if len(self.console_errors) == 0:
#             return {"status": "PASS", "details": "No console errors"}
#         return {
#             "status": "FAIL",
#             "details": f"{len(self.console_errors)} console errors: {self.console_errors[:3]}"
#         }

#     def _test_button_click(self, tc):
#         url = tc["target_url"]
#         btn_text = tc["button_text"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             btn = self.page.locator(f'button:has-text("{btn_text}")').first
#             if btn.is_visible(timeout=3000):
#                 btn.click()
#                 self.page.wait_for_timeout(1000)
#                 return {"status": "PASS", "details": f"Clicked '{btn_text}' successfully"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Could not click '{btn_text}': {str(e)[:100]}"}
#         return {"status": "FAIL", "details": f"Button '{btn_text}' not visible"}

#     def _test_input_fill(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             inputs = self.page.locator("input:visible").all()
#             if inputs:
#                 first_input = inputs[0]
#                 first_input.fill("test_input_123")
#                 self.page.wait_for_timeout(500)
#                 value = first_input.input_value()
#                 if "test_input_123" in value:
#                     first_input.fill("")
#                     return {"status": "PASS", "details": "Input accepted text"}
#                 return {"status": "FAIL", "details": "Input did not retain value"}
#             return {"status": "FAIL", "details": "No visible inputs found"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Input error: {str(e)[:100]}"}

#     def _test_table(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             rows = self.page.locator("table tbody tr").count()
#             if rows > 0:
#                 return {"status": "PASS", "details": f"Table has {rows} rows"}
#             return {"status": "FAIL", "details": "Table has no rows"}
#         except Exception:
#             return {"status": "FAIL", "details": "Could not find table rows"}

#     def _test_cross_nav(self, tc):
#         from_url = tc["from_url"]
#         to_url = tc["to_url"]
#         to_name = tc["to_name"]
#         self.page.goto(from_url, wait_until="networkidle", timeout=15000)
#         try:
#             link = self.page.locator(f'a:has-text("{to_name}")').first
#             if link.is_visible(timeout=3000):
#                 link.click()
#                 self.page.wait_for_load_state("networkidle", timeout=10000)
#                 current = self.page.url
#                 if to_name.lower() in current.lower() or current == to_url:
#                     return {"status": "PASS", "details": f"Navigated to {current}"}
#                 return {"status": "FAIL", "details": f"Expected {to_url}, got {current}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Nav failed: {str(e)[:100]}"}
#         return {"status": "FAIL", "details": f"Link to '{to_name}' not found"}

#     def _test_not_blank(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         content = self.page.content()
#         body_text = self.page.locator("body").inner_text()
#         if len(body_text.strip()) > 10:
#             return {"status": "PASS", "details": f"Page has content ({len(body_text)} chars)"}
#         return {"status": "FAIL", "details": "Page appears blank"}

#     def _test_logout(self, tc):
#         try:
#             for kw in ["profile", "settings", "account"]:
#                 candidate = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/{kw}"
#                 try:
#                     self.page.goto(candidate, wait_until="networkidle", timeout=10000)
#                     break
#                 except Exception:
#                     continue

#             logout_selectors = [
#                 'button:has-text("Logout")',
#                 'button:has-text("Log out")',
#                 'a:has-text("Logout")',
#                 'a:has-text("Log out")',
#             ]

#             for sel in logout_selectors:
#                 try:
#                     btn = self.page.locator(sel).first
#                     if btn.is_visible(timeout=3000):
#                         btn.click()
#                         self.page.wait_for_timeout(3000)
#                         current = self.page.url.lower()
#                         if "login" in current:
#                             return {"status": "PASS", "details": "Logged out successfully"}
#                         return {"status": "PASS", "details": f"Logout clicked, at: {self.page.url}"}
#                 except Exception:
#                     continue

#             return {"status": "FAIL", "details": "Logout button not found"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Logout error: {str(e)[:100]}"}
        

        










# from utils.logger import log
# import config
# import os

# class Executor:
#     def __init__(self, page):
#         self.page = page
#         self.console_errors = []
#         self.page.on("console", self._capture_console)

#     def _capture_console(self, msg):
#         if msg.type == "error":
#             self.console_errors.append(msg.text)

#     def navigate(self, url):
#         log(f"Navigating to: {url}")
#         self.page.goto(url, wait_until="networkidle")
#         log(f"Loaded: {self.page.title()}")

#     def find_and_fill(self, selectors, value, field_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.fill(value)
#                     log(f"Filled '{field_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue
#         log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
#         return False

#     def find_and_click(self, selectors, button_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.click()
#                     log(f"Clicked '{button_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue
#         log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
#         return False

#     def login(self):
#         log("=" * 50)
#         log("LOGIN PHASE STARTED")
#         log("=" * 50)

#         self.navigate(config.APP_URL)
#         self.take_screenshot("01_login_page")
#         login_url = self.page.url

#         username_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["username"],
#             config.USERNAME,
#             "username"
#         )

#         password_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["password"],
#             config.PASSWORD,
#             "password"
#         )

#         if not username_ok or not password_ok:
#             log("Login aborted: could not find input fields", level="ERROR")
#             self.take_screenshot("login_field_error")
#             return False

#         submit_ok = self.find_and_click(
#             config.LOGIN_SELECTORS["submit"],
#             "login button"
#         )

#         if not submit_ok:
#             log("Login aborted: could not find submit button", level="ERROR")
#             self.take_screenshot("login_button_error")
#             return False

#         log("Waiting for redirect after login...")

#         try:
#             self.page.wait_for_url(
#                 lambda url: url != login_url,
#                 timeout=15000
#             )
#             log(f"URL changed to: {self.page.url}")
#         except Exception:
#             log("URL did not change — trying alternative waits", level="WARN")

#         try:
#             self.page.wait_for_load_state("networkidle", timeout=10000)
#         except Exception:
#             log("Network idle timeout", level="WARN")

#         try:
#             self.page.wait_for_timeout(3000)
#         except Exception:
#             pass

#         log(f"Final URL after login: {self.page.url}")
#         self.take_screenshot("02_after_login")
#         return True

#     def take_screenshot(self, name):
#         os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
#         path = f"{config.SCREENSHOT_DIR}/{name}.png"
#         self.page.screenshot(path=path)
#         log(f"Screenshot saved: {name}.png")

#     def get_current_url(self):
#         return self.page.url

#     def get_page_title(self):
#         return self.page.title()

#     def run_test(self, test_case):
#         test_type = test_case["type"]
#         try:
#             if test_type == "page_load":
#                 return self._test_page_load(test_case)
#             elif test_type == "login":
#                 return self._test_login(test_case)
#             elif test_type == "element_exists":
#                 return self._test_element_exists(test_case)
#             elif test_type == "title_check":
#                 return self._test_title(test_case)
#             elif test_type == "console_check":
#                 return self._test_console(test_case)
#             elif test_type == "button_click":
#                 return self._test_button_click(test_case)
#             elif test_type == "input_fill":
#                 return self._test_input_fill(test_case)
#             elif test_type == "table_check":
#                 return self._test_table(test_case)
#             elif test_type == "cross_navigation":
#                 return self._test_cross_nav(test_case)
#             elif test_type == "not_blank":
#                 return self._test_not_blank(test_case)
#             elif test_type == "logout":
#                 return self._test_logout(test_case)
#             else:
#                 return {"status": "SKIP", "details": f"Unknown test type: {test_type}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Exception: {str(e)[:200]}"}

#     def _test_page_load(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         current = self.page.url
#         title = self.page.title()
#         if title and len(self.page.content()) > 100:
#             return {"status": "PASS", "details": f"Page loaded: {title}"}
#         return {"status": "FAIL", "details": f"Page may not have loaded properly at {current}"}

#     def _test_login(self, tc):
#         current = self.page.url.lower()
#         if "dashboard" in current or "app" in current:
#             return {"status": "PASS", "details": f"Logged in at: {self.page.url}"}
#         return {"status": "FAIL", "details": f"Not on dashboard: {self.page.url}"}

#     def _test_element_exists(self, tc):
#         url = tc.get("target_url", "")
#         if url:
#             self.page.goto(url, wait_until="networkidle", timeout=15000)
#         selectors = tc["selector"]
#         for sel in selectors:
#             try:
#                 element = self.page.locator(sel).first
#                 if element.is_visible(timeout=3000):
#                     return {"status": "PASS", "details": f"Found element: {sel}"}
#             except Exception:
#                 continue
#         return {"status": "FAIL", "details": "Element not found with any selector"}

#     def _test_title(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         title = self.page.title()
#         if title and len(title.strip()) > 0:
#             return {"status": "PASS", "details": f"Title: {title}"}
#         return {"status": "FAIL", "details": "Page has no title"}

#     def _test_console(self, tc):
#         url = tc["target_url"]
#         self.console_errors = []
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         self.page.wait_for_timeout(2000)
#         if len(self.console_errors) == 0:
#             return {"status": "PASS", "details": "No console errors"}
#         return {
#             "status": "FAIL",
#             "details": f"{len(self.console_errors)} console errors: {self.console_errors[:3]}"
#         }

#     def _test_button_click(self, tc):
#         url = tc["target_url"]
#         btn_text = tc["button_text"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             btn = self.page.locator(f'button:has-text("{btn_text}")').first
#             if btn.is_visible(timeout=3000):
#                 btn.click()
#                 self.page.wait_for_timeout(1000)
#                 return {"status": "PASS", "details": f"Clicked '{btn_text}' successfully"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Could not click '{btn_text}': {str(e)[:100]}"}
#         return {"status": "FAIL", "details": f"Button '{btn_text}' not visible"}

#     def _test_input_fill(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             inputs = self.page.locator("input:visible").all()
#             if inputs:
#                 first_input = inputs[0]
#                 first_input.fill("test_input_123")
#                 self.page.wait_for_timeout(500)
#                 value = first_input.input_value()
#                 if "test_input_123" in value:
#                     first_input.fill("")
#                     return {"status": "PASS", "details": "Input accepted text"}
#                 return {"status": "FAIL", "details": "Input did not retain value"}
#             return {"status": "FAIL", "details": "No visible inputs found"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Input error: {str(e)[:100]}"}

#     def _test_table(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         try:
#             rows = self.page.locator("table tbody tr").count()
#             if rows > 0:
#                 return {"status": "PASS", "details": f"Table has {rows} rows"}
#             return {"status": "FAIL", "details": "Table has no rows"}
#         except Exception:
#             return {"status": "FAIL", "details": "Could not find table rows"}

#     def _test_cross_nav(self, tc):
#         from_url = tc["from_url"]
#         to_url = tc["to_url"]
#         to_name = tc["to_name"]
#         self.page.goto(from_url, wait_until="networkidle", timeout=15000)
#         try:
#             link = self.page.locator(f'a:has-text("{to_name}")').first
#             if link.is_visible(timeout=3000):
#                 link.click()
#                 self.page.wait_for_load_state("networkidle", timeout=10000)
#                 current = self.page.url
#                 if to_name.lower() in current.lower() or current == to_url:
#                     return {"status": "PASS", "details": f"Navigated to {current}"}
#                 return {"status": "FAIL", "details": f"Expected {to_url}, got {current}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Nav failed: {str(e)[:100]}"}
#         return {"status": "FAIL", "details": f"Link to '{to_name}' not found"}

#     def _test_not_blank(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         content = self.page.content()
#         body_text = self.page.locator("body").inner_text()
#         if len(body_text.strip()) > 10:
#             return {"status": "PASS", "details": f"Page has content ({len(body_text)} chars)"}
#         return {"status": "FAIL", "details": "Page appears blank"}

#     def _test_logout(self, tc):
#         try:
#             for kw in ["profile", "settings", "account"]:
#                 candidate = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/{kw}"
#                 try:
#                     self.page.goto(candidate, wait_until="networkidle", timeout=10000)
#                     break
#                 except Exception:
#                     continue

#             logout_selectors = [
#                 'button:has-text("Logout")',
#                 'button:has-text("Log out")',
#                 'a:has-text("Logout")',
#                 'a:has-text("Log out")',
#             ]

#             for sel in logout_selectors:
#                 try:
#                     btn = self.page.locator(sel).first
#                     if btn.is_visible(timeout=3000):
#                         btn.click()
#                         self.page.wait_for_timeout(3000)
#                         current = self.page.url.lower()
#                         if "login" in current:
#                             return {"status": "PASS", "details": "Logged out successfully"}
#                         return {"status": "PASS", "details": f"Logout clicked, at: {self.page.url}"}
#                 except Exception:
#                     continue

#             return {"status": "FAIL", "details": "Logout button not found"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Logout error: {str(e)[:100]}"}











# from utils.logger import log
# import config
# import os

# from utils.logger import log
# import config
# import os

# class Executor:
#     def __init__(self, page):
#         self.page = page
#         self.console_errors = []

#         # Listen for console errors
#         self.page.on("console", self._capture_console)

#     def _capture_console(self, msg):
#         if msg.type == "error":
#             self.console_errors.append(msg.text)

#     def navigate(self, url):
#         log(f"Navigating to: {url}")
#         self.page.goto(url, wait_until="networkidle")
#         log(f"Loaded: {self.page.title()}")

#     def find_and_fill(self, selectors, value, field_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.fill(value)
#                     log(f"Filled '{field_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue

#         log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
#         return False

#     def find_and_click(self, selectors, button_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.click()
#                     log(f"Clicked '{button_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue

#         log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
#         return False

#     def login(self):
#         log("=" * 50)
#         log("LOGIN PHASE STARTED")
#         log("=" * 50)

#         self.navigate(config.APP_URL)
#         self.take_screenshot("01_login_page")

#         login_url = self.page.url

#         username_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["username"],
#             config.USERNAME,
#             "username"
#         )

#         password_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["password"],
#             config.PASSWORD,
#             "password"
#         )

#         if not username_ok or not password_ok:
#             log("Login aborted: could not find input fields", level="ERROR")
#             self.take_screenshot("login_field_error")
#             return False

#         submit_ok = self.find_and_click(
#             config.LOGIN_SELECTORS["submit"],
#             "login button"
#         )

#         if not submit_ok:
#             log("Login aborted: could not find submit button", level="ERROR")
#             self.take_screenshot("login_button_error")
#             return False

#         log("Waiting for redirect after login...")

#         try:
#             self.page.wait_for_url(
#                 lambda url: url != login_url,
#                 timeout=15000
#             )
#             log(f"URL changed to: {self.page.url}")
#         except Exception:
#             log("URL did not change — trying alternative waits", level="WARN")

#         try:
#             self.page.wait_for_load_state("networkidle", timeout=10000)
#         except Exception:
#             log("Network idle timeout", level="WARN")

#         try:
#             self.page.wait_for_timeout(3000)
#         except Exception:
#             pass

#         log(f"Final URL after login: {self.page.url}")
#         self.take_screenshot("02_after_login")

#         return True

#     def take_screenshot(self, name):
#         os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
#         path = f"{config.SCREENSHOT_DIR}/{name}.png"
#         self.page.screenshot(path=path)
#         log(f"Screenshot saved: {name}.png")

#     def get_current_url(self):
#         return self.page.url

#     def get_page_title(self):
#         return self.page.title()

#     # =============================================
#     # NEW: Test Execution Methods (Phase 4)
#     # =============================================

#     def run_test(self, test_case):
#         """Execute a single test case and return result"""
#         test_type = test_case["type"]

#         try:
#             if test_type == "page_load":
#                 return self._test_page_load(test_case)
#             elif test_type == "login":
#                 return self._test_login(test_case)
#             elif test_type == "element_exists":
#                 return self._test_element_exists(test_case)
#             elif test_type == "title_check":
#                 return self._test_title(test_case)
#             elif test_type == "console_check":
#                 return self._test_console(test_case)
#             elif test_type == "button_click":
#                 return self._test_button_click(test_case)
#             elif test_type == "input_fill":
#                 return self._test_input_fill(test_case)
#             elif test_type == "table_check":
#                 return self._test_table(test_case)
#             elif test_type == "cross_navigation":
#                 return self._test_cross_nav(test_case)
#             elif test_type == "not_blank":
#                 return self._test_not_blank(test_case)
#             elif test_type == "logout":
#                 return self._test_logout(test_case)
#             else:
#                 return {"status": "SKIP", "details": f"Unknown test type: {test_type}"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Exception: {str(e)[:200]}"}

#     def _test_page_load(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         current = self.page.url
#         title = self.page.title()
#         if title and len(self.page.content()) > 100:
#             return {"status": "PASS", "details": f"Page loaded: {title}"}
#         return {"status": "FAIL", "details": f"Page may not have loaded properly at {current}"}

#     def _test_login(self, tc):
#         # Already logged in from Phase 2, just verify
#         current = self.page.url.lower()
#         if "dashboard" in current or "app" in current:
#             return {"status": "PASS", "details": f"Logged in at: {self.page.url}"}
#         return {"status": "FAIL", "details": f"Not on dashboard: {self.page.url}"}

#     def _test_element_exists(self, tc):
#         url = tc.get("target_url", "")
#         if url:
#             self.page.goto(url, wait_until="networkidle", timeout=15000)

#         selectors = tc["selector"]
#         for sel in selectors:
#             try:
#                 element = self.page.locator(sel).first
#                 if element.is_visible(timeout=3000):
#                     return {"status": "PASS", "details": f"Found element: {sel}"}
#             except Exception:
#                 continue

#         return {"status": "FAIL", "details": "Element not found with any selector"}

#     def _test_title(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         title = self.page.title()
#         if title and len(title.strip()) > 0:
#             return {"status": "PASS", "details": f"Title: {title}"}
#         return {"status": "FAIL", "details": "Page has no title"}

#     def _test_console(self, tc):
#         url = tc["target_url"]
#         self.console_errors = []
#         self.page.goto(url, wait_until="networkidle", timeout=15000)
#         self.page.wait_for_timeout(2000)

#         if len(self.console_errors) == 0:
#             return {"status": "PASS", "details": "No console errors"}
#         return {
#             "status": "FAIL",
#             "details": f"{len(self.console_errors)} console errors: {self.console_errors[:3]}"
#         }

#     def _test_button_click(self, tc):
#         url = tc["target_url"]
#         btn_text = tc["button_text"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             btn = self.page.locator(f'button:has-text("{btn_text}")').first
#             if btn.is_visible(timeout=3000):
#                 btn.click()
#                 self.page.wait_for_timeout(1000)
#                 return {"status": "PASS", "details": f"Clicked '{btn_text}' successfully"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Could not click '{btn_text}': {str(e)[:100]}"}

#         return {"status": "FAIL", "details": f"Button '{btn_text}' not visible"}

#     def _test_input_fill(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             inputs = self.page.locator("input:visible").all()
#             if inputs:
#                 first_input = inputs[0]
#                 first_input.fill("test_input_123")
#                 self.page.wait_for_timeout(500)
#                 value = first_input.input_value()
#                 if "test_input_123" in value:
#                     # Clear after test
#                     first_input.fill("")
#                     return {"status": "PASS", "details": "Input accepted text"}
#                 return {"status": "FAIL", "details": "Input did not retain value"}
#             return {"status": "FAIL", "details": "No visible inputs found"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Input error: {str(e)[:100]}"}

#     def _test_table(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         try:
#             rows = self.page.locator("table tbody tr").count()
#             if rows > 0:
#                 return {"status": "PASS", "details": f"Table has {rows} rows"}
#             return {"status": "FAIL", "details": "Table has no rows"}
#         except Exception:
#             return {"status": "FAIL", "details": "Could not find table rows"}

#     def _test_cross_nav(self, tc):
#         from_url = tc["from_url"]
#         to_url = tc["to_url"]
#         to_name = tc["to_name"]

#         self.page.goto(from_url, wait_until="networkidle", timeout=15000)

#         try:
#             link = self.page.locator(f'a:has-text("{to_name}")').first
#             if link.is_visible(timeout=3000):
#                 link.click()
#                 self.page.wait_for_load_state("networkidle", timeout=10000)
#                 current = self.page.url
#                 if to_name.lower() in current.lower() or current == to_url:
#                     return {"status": "PASS", "details": f"Navigated to {current}"}
#                 return {"status": "FAIL", "details": f"Expected {to_url}, got {current}"}
#         except Exception as e:
#             return {"status": "FAIL", "details": f"Nav failed: {str(e)[:100]}"}

#         return {"status": "FAIL", "details": f"Link to '{to_name}' not found"}

#     def _test_not_blank(self, tc):
#         url = tc["target_url"]
#         self.page.goto(url, wait_until="networkidle", timeout=15000)

#         content = self.page.content()
#         body_text = self.page.locator("body").inner_text()

#         if len(body_text.strip()) > 10:
#             return {"status": "PASS", "details": f"Page has content ({len(body_text)} chars)"}
#         return {"status": "FAIL", "details": "Page appears blank"}

#     def _test_logout(self, tc):
#         # Find and click logout
#         try:
#             # Go to profile where logout button was found
#             profile_url = None
#             for kw in ["profile", "settings", "account"]:
#                 candidate = f"https://{config.ALLOWED_DOMAIN}/weatherseal-operations-fe/app/{kw}"
#                 try:
#                     self.page.goto(candidate, wait_until="networkidle", timeout=10000)
#                     profile_url = candidate
#                     break
#                 except Exception:
#                     continue

#             logout_selectors = [
#                 'button:has-text("Logout")',
#                 'button:has-text("Log out")',
#                 'a:has-text("Logout")',
#                 'a:has-text("Log out")',
#             ]

#             for sel in logout_selectors:
#                 try:
#                     btn = self.page.locator(sel).first
#                     if btn.is_visible(timeout=3000):
#                         btn.click()
#                         self.page.wait_for_timeout(3000)
#                         current = self.page.url.lower()
#                         if "login" in current:
#                             return {"status": "PASS", "details": "Logged out successfully"}
#                         return {"status": "PASS", "details": f"Logout clicked, at: {self.page.url}"}
#                 except Exception:
#                     continue

#             return {"status": "FAIL", "details": "Logout button not found"}

#         except Exception as e:
#             return {"status": "FAIL", "details": f"Logout error: {str(e)[:100]}"}

# class Executor:
#     def __init__(self, page):
#         self.page = page

#     def navigate(self, url):
#         log(f"Navigating to: {url}")
#         self.page.goto(url, wait_until="networkidle")
#         log(f"Loaded: {self.page.title()}")

#     def find_and_fill(self, selectors, value, field_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.fill(value)
#                     log(f"Filled '{field_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue

#         log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
#         return False

#     def find_and_click(self, selectors, button_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.click()
#                     log(f"Clicked '{button_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue

#         log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
#         return False

#     def login(self):
#         log("=" * 50)
#         log("LOGIN PHASE STARTED")
#         log("=" * 50)

#         # Navigate to login page
#         self.navigate(config.APP_URL)

#         # Screenshot before login
#         self.take_screenshot("01_login_page")

#         # Capture login page URL to compare later
#         login_url = self.page.url

#         # Fill username
#         username_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["username"],
#             config.USERNAME,
#             "username"
#         )

#         # Fill password
#         password_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["password"],
#             config.PASSWORD,
#             "password"
#         )

#         if not username_ok or not password_ok:
#             log("Login aborted: could not find input fields", level="ERROR")
#             self.take_screenshot("login_field_error")
#             return False

#         # Click submit
#         submit_ok = self.find_and_click(
#             config.LOGIN_SELECTORS["submit"],
#             "login button"
#         )

#         if not submit_ok:
#             log("Login aborted: could not find submit button", level="ERROR")
#             self.take_screenshot("login_button_error")
#             return False

#         # WAIT for navigation/redirect after login
#         log("Waiting for redirect after login...")

#         # Strategy 1: Wait for URL to change
#         try:
#             self.page.wait_for_url(
#                 lambda url: url != login_url,
#                 timeout=15000
#             )
#             log(f"URL changed to: {self.page.url}")
#         except Exception:
#             log("URL did not change — trying alternative waits", level="WARN")

#         # Strategy 2: Wait for network to settle
#         try:
#             self.page.wait_for_load_state("networkidle", timeout=10000)
#         except Exception:
#             log("Network idle timeout", level="WARN")

#         # Strategy 3: Extra wait for SPA apps
#         try:
#             self.page.wait_for_timeout(3000)
#         except Exception:
#             pass

#         log(f"Final URL after login: {self.page.url}")

#         # Screenshot after login attempt
#         self.take_screenshot("02_after_login")

#         return True

#     def take_screenshot(self, name):
#         os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
#         path = f"{config.SCREENSHOT_DIR}/{name}.png"
#         self.page.screenshot(path=path)
#         log(f"Screenshot saved: {name}.png")

#     def get_current_url(self):
#         return self.page.url

#     def get_page_title(self):
#         return self.page.title()


# from utils.logger import log
# import config
# import os

# class Executor:
#     def __init__(self, page):
#         self.page = page

#     def navigate(self, url):
#         log(f"Navigating to: {url}")
#         self.page.goto(url, wait_until="networkidle")
#         log(f"Loaded: {self.page.title()}")

#     def find_and_fill(self, selectors, value, field_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.fill(value)
#                     log(f"Filled '{field_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue

#         log(f"FAILED: Could not find '{field_name}' field", level="ERROR")
#         return False

#     def find_and_click(self, selectors, button_name):
#         for selector in selectors:
#             try:
#                 element = self.page.locator(selector).first
#                 if element.is_visible(timeout=3000):
#                     element.click()
#                     log(f"Clicked '{button_name}' using selector: {selector}")
#                     return True
#             except Exception:
#                 continue

#         log(f"FAILED: Could not find '{button_name}' button", level="ERROR")
#         return False

#     def login(self):
#         log("=" * 50)
#         log("LOGIN PHASE STARTED")
#         log("=" * 50)

#         # Navigate to login page
#         self.navigate(config.APP_URL)

#         # Screenshot before login
#         self.take_screenshot("01_login_page")

#         # Capture login page URL to compare later
#         login_url = self.page.url

#         # Fill username
#         username_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["username"],
#             config.USERNAME,
#             "username"
#         )

#         # Fill password
#         password_ok = self.find_and_fill(
#             config.LOGIN_SELECTORS["password"],
#             config.PASSWORD,
#             "password"
#         )

#         if not username_ok or not password_ok:
#             log("Login aborted: could not find input fields", level="ERROR")
#             self.take_screenshot("login_field_error")
#             return False

#         # Click submit
#         submit_ok = self.find_and_click(
#             config.LOGIN_SELECTORS["submit"],
#             "login button"
#         )

#         if not submit_ok:
#             log("Login aborted: could not find submit button", level="ERROR")
