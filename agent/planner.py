
from utils.logger import log
from urllib.parse import urlparse
import config


class Planner:
    def __init__(self, page, url=None):
        self.page = page
        self.discovered_pages = []
        self.visited_urls = set()
        self.page_map = []
        self.generated_tests = []
        self.app_url = url or config.APP_URL
        if url:
            parsed = urlparse(url)
            self.allowed_domain = parsed.netloc
        else:
            self.allowed_domain = config.ALLOWED_DOMAIN

    def discover_links(self):
        log("=" * 50)
        log("DISCOVERY PHASE STARTED")
        log("=" * 50)

        links_found = []

        for selector in config.NAV_SELECTORS:
            try:
                elements = self.page.locator(selector).all()
                for element in elements:
                    try:
                        href = element.get_attribute("href") or ""
                        text = element.inner_text().strip()

                        if not text:
                            text = element.get_attribute("aria-label") or "unknown"

                        if self._should_skip(href, text):
                            continue

                        full_url = self._resolve_url(href)

                        if full_url and full_url not in [l["url"] for l in links_found]:
                            links_found.append({
                                "text": text,
                                "url": full_url,
                                "selector": selector
                            })

                    except Exception:
                        continue
            except Exception:
                continue

        unique_links = []
        seen_urls = set()
        for link in links_found:
            if link["url"] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link["url"])

        log(f"Discovered {len(unique_links)} unique navigation links")
        for i, link in enumerate(unique_links):
            log(f"  [{i+1}] {link['text']} -> {link['url']}")

        self.discovered_pages = unique_links
        return unique_links

    def discover_clickable_elements(self):
        elements_found = {
            "buttons": [],
            "forms": [],
            "tables": [],
            "inputs": [],
            "dropdowns": []
        }

        try:
            buttons = self.page.locator("button").all()
            for btn in buttons:
                try:
                    text = btn.inner_text().strip()
                    if text and len(text) < 50:
                        elements_found["buttons"].append(text)
                except Exception:
                    continue
        except Exception:
            pass

        try:
            forms = self.page.locator("form").count()
            elements_found["forms"] = forms
        except Exception:
            elements_found["forms"] = 0

        try:
            tables = self.page.locator("table").count()
            elements_found["tables"] = tables
        except Exception:
            elements_found["tables"] = 0

        try:
            inputs = self.page.locator("input:visible").all()
            for inp in inputs:
                try:
                    inp_type = inp.get_attribute("type") or "text"
                    inp_name = inp.get_attribute("name") or inp.get_attribute("placeholder") or "unnamed"
                    elements_found["inputs"].append(f"{inp_type}:{inp_name}")
                except Exception:
                    continue
        except Exception:
            pass

        try:
            selects = self.page.locator("select").count()
            elements_found["dropdowns"] = selects
        except Exception:
            elements_found["dropdowns"] = 0

        return elements_found

    def build_page_map(self, executor):
        log("=" * 50)
        log("PAGE MAPPING STARTED")
        log("=" * 50)

        base_url = self.page.url
        self.visited_urls.add(base_url)

        dashboard_elements = self.discover_clickable_elements()
        self.page_map.append({
            "page_name": "Dashboard",
            "url": base_url,
            "title": self.page.title(),
            "elements": dashboard_elements
        })
        log(f"Mapped: Dashboard -> {base_url}")
        self._log_elements(dashboard_elements)

        for i, link in enumerate(self.discovered_pages):
            if len(self.page_map) >= config.MAX_PAGES:
                log(f"Reached max pages limit ({config.MAX_PAGES})")
                break

            if link["url"] in self.visited_urls:
                continue

            log(f"\n--- Visiting [{i+1}/{len(self.discovered_pages)}]: {link['text']} ---")

            try:
                self.page.goto(link["url"], wait_until="networkidle", timeout=15000)
                self.visited_urls.add(link["url"])
                self.page.wait_for_load_state("domcontentloaded")

                page_title = self.page.title()
                current_url = self.page.url

                elements = self.discover_clickable_elements()

                executor.take_screenshot(f"page_{i+1}_{self._safe_name(link['text'])}")

                self.page_map.append({
                    "page_name": link["text"],
                    "url": current_url,
                    "title": page_title,
                    "elements": elements
                })

                log(f"Mapped: {link['text']} -> {current_url}")
                self._log_elements(elements)

                sub_links = self._find_new_links()
                for sub in sub_links:
                    if sub["url"] not in self.visited_urls and sub not in self.discovered_pages:
                        self.discovered_pages.append(sub)
                        log(f"  [NEW] Found sub-link: {sub['text']} -> {sub['url']}")

            except Exception as e:
                log(f"Failed to visit: {link['text']} -> {str(e)[:100]}", level="ERROR")
                executor.take_screenshot(f"error_page_{i+1}")
                continue

        log("=" * 50)
        log(f"PAGE MAPPING COMPLETE: {len(self.page_map)} pages mapped")
        log("=" * 50)

        return self.page_map

    def _find_new_links(self):
        new_links = []
        for selector in config.NAV_SELECTORS:
            try:
                elements = self.page.locator(selector).all()
                for element in elements:
                    try:
                        href = element.get_attribute("href") or ""
                        text = element.inner_text().strip()
                        if not text:
                            continue
                        if self._should_skip(href, text):
                            continue
                        full_url = self._resolve_url(href)
                        if full_url and full_url not in self.visited_urls:
                            new_links.append({"text": text, "url": full_url, "selector": selector})
                    except Exception:
                        continue
            except Exception:
                continue
        return new_links

    def _should_skip(self, href, text):
        combined = (href + text).lower()
        for keyword in config.SKIP_KEYWORDS:
            if keyword in combined:
                return True
        if href.startswith("http") and self.allowed_domain not in href:
            return True
        if not href or href == "/" or href == "#":
            return True
        return False

    def _resolve_url(self, href):
        if not href:
            return None
        if href.startswith("http"):
            return href
        base = f"https://{self.allowed_domain}"
        if href.startswith("/"):
            return base + href
        return base + "/" + href

    def _safe_name(self, text):
        safe = "".join(c if c.isalnum() else "_" for c in text)
        return safe[:30]

    def _log_elements(self, elements):
        log(f"  Buttons: {len(elements['buttons'])} -> {elements['buttons'][:5]}")
        log(f"  Forms: {elements['forms']}")
        log(f"  Tables: {elements['tables']}")
        log(f"  Inputs: {len(elements['inputs'])}")
        log(f"  Dropdowns: {elements['dropdowns']}")

    def get_summary(self):
        return {
            "total_pages": len(self.page_map),
            "total_links_found": len(self.discovered_pages),
            "pages": [
                {
                    "name": p["page_name"],
                    "url": p["url"],
                    "buttons": len(p["elements"]["buttons"]),
                    "forms": p["elements"]["forms"],
                    "tables": p["elements"]["tables"],
                    "inputs": len(p["elements"]["inputs"]),
                }
                for p in self.page_map
            ]
        }

    def generate_test_cases(self):
        log("=" * 50)
        log("TEST CASE GENERATION STARTED")
        log("=" * 50)

        test_id = 0
        tests = []

        # ============================================
        # CATEGORY 1: Login Tests
        # ============================================

        test_id += 1
        tests.append({
            "id": f"TC_{test_id:03d}",
            "name": "Verify login page loads",
            "category": "Login",
            "type": "page_load",
            "target_url": self.app_url,
            "action": "navigate",
            "expected": "page_loads"
        })

        test_id += 1
        tests.append({
            "id": f"TC_{test_id:03d}",
            "name": "Verify login with valid credentials",
            "category": "Login",
            "type": "login",
            "action": "login",
            "expected": "redirect_to_dashboard"
        })

        test_id += 1
        tests.append({
            "id": f"TC_{test_id:03d}",
            "name": "Verify login page has username field",
            "category": "Login",
            "type": "element_exists",
            "target_url": self.app_url,
            "selector": config.LOGIN_SELECTORS["username"],
            "expected": "element_visible"
        })

        test_id += 1
        tests.append({
            "id": f"TC_{test_id:03d}",
            "name": "Verify login page has password field",
            "category": "Login",
            "type": "element_exists",
            "target_url": self.app_url,
            "selector": config.LOGIN_SELECTORS["password"],
            "expected": "element_visible"
        })

        test_id += 1
        tests.append({
            "id": f"TC_{test_id:03d}",
            "name": "Verify login page has submit button",
            "category": "Login",
            "type": "element_exists",
            "target_url": self.app_url,
            "selector": config.LOGIN_SELECTORS["submit"],
            "expected": "element_visible"
        })

        # ============================================
        # CATEGORY 2: Navigation Tests (per page)
        # ============================================

        for page_info in self.page_map:
            page_name = page_info["page_name"]
            page_url = page_info["url"]

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify '{page_name}' page loads successfully",
                "category": "Navigation",
                "type": "page_load",
                "target_url": page_url,
                "action": "navigate",
                "expected": "page_loads"
            })

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify '{page_name}' page has valid title",
                "category": "Navigation",
                "type": "title_check",
                "target_url": page_url,
                "expected": "title_not_empty"
            })

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify '{page_name}' page has no console errors",
                "category": "Navigation",
                "type": "console_check",
                "target_url": page_url,
                "expected": "no_errors"
            })

        # ============================================
        # CATEGORY 3: Button Tests
        # ============================================

        for page_info in self.page_map:
            page_name = page_info["page_name"]
            page_url = page_info["url"]
            buttons = page_info["elements"].get("buttons", [])

            for btn_text in buttons:
                if btn_text.lower() in ["logout", "log out", "sign out"]:
                    continue

                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify '{btn_text}' button is clickable on '{page_name}'",
                    "category": "Button",
                    "type": "button_click",
                    "target_url": page_url,
                    "button_text": btn_text,
                    "expected": "click_success"
                })

        # ============================================
        # CATEGORY 4: Input Field Tests
        # ============================================

        for page_info in self.page_map:
            page_name = page_info["page_name"]
            page_url = page_info["url"]
            inputs = page_info["elements"].get("inputs", [])

            for inp in inputs:
                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify input '{inp}' accepts text on '{page_name}'",
                    "category": "Input",
                    "type": "input_fill",
                    "target_url": page_url,
                    "input_info": inp,
                    "expected": "input_accepts_text"
                })

        # ============================================
        # CATEGORY 5: Table Tests
        # ============================================

        for page_info in self.page_map:
            page_name = page_info["page_name"]
            page_url = page_info["url"]
            tables = page_info["elements"].get("tables", 0)

            if tables > 0:
                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify table has data on '{page_name}'",
                    "category": "Table",
                    "type": "table_check",
                    "target_url": page_url,
                    "expected": "table_has_rows"
                })

        # ============================================
        # CATEGORY 6: Cross-Navigation Tests
        # ============================================

        if len(self.page_map) >= 2:
            for i in range(len(self.page_map) - 1):
                from_page = self.page_map[i]
                to_page = self.page_map[i + 1]

                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Navigate from '{from_page['page_name']}' to '{to_page['page_name']}'",
                    "category": "CrossNav",
                    "type": "cross_navigation",
                    "from_url": from_page["url"],
                    "to_url": to_page["url"],
                    "to_name": to_page["page_name"],
                    "expected": "navigation_success"
                })

        # ============================================
        # CATEGORY 7: Structure Tests
        # ============================================

        for page_info in self.page_map:
            page_name = page_info["page_name"]
            page_url = page_info["url"]

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify '{page_name}' page is not blank",
                "category": "Structure",
                "type": "not_blank",
                "target_url": page_url,
                "expected": "page_has_content"
            })

        # ============================================
        # CATEGORY 8: Deep Functional Tests
        # ============================================

        for page_info in self.page_map:
            page_name = page_info["page_name"]
            page_url = page_info["url"]
            buttons = page_info["elements"].get("buttons", [])
            inputs = page_info["elements"].get("inputs", [])
            tables = page_info["elements"].get("tables", 0)

            if inputs and any(b.lower() in ["search", "find", "go", "filter", "apply"] for b in buttons):
                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify search/filter works on '{page_name}'",
                    "category": "DeepFunctional",
                    "type": "search_workflow",
                    "target_url": page_url,
                    "expected": "page_content_changes"
                })

            sort_buttons = [b for b in buttons if any(kw in b.lower() for kw in ["sort", "newest", "oldest", "a-z", "z-a", "first", "last", "ascending", "descending"])]
            for sort_btn in sort_buttons:
                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify sort '{sort_btn}' changes content on '{page_name}'",
                    "category": "DeepFunctional",
                    "type": "sort_workflow",
                    "target_url": page_url,
                    "button_text": sort_btn,
                    "expected": "content_changes_after_sort"
                })

            filter_buttons = [b for b in buttons if any(kw in b.lower() for kw in ["all", "active", "inactive", "pending", "completed", "open", "closed", "approved", "rejected"])]
            for filter_btn in filter_buttons:
                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify filter '{filter_btn}' works on '{page_name}'",
                    "category": "DeepFunctional",
                    "type": "filter_workflow",
                    "target_url": page_url,
                    "button_text": filter_btn,
                    "expected": "content_changes_after_filter"
                })

            if page_info["elements"].get("forms", 0) > 0 and inputs:
                test_id += 1
                tests.append({
                    "id": f"TC_{test_id:03d}",
                    "name": f"Verify form submission on '{page_name}'",
                    "category": "DeepFunctional",
                    "type": "form_workflow",
                    "target_url": page_url,
                    "expected": "form_submits_successfully"
                })

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify '{page_name}' handles empty interactions gracefully",
                "category": "DeepFunctional",
                "type": "error_handling",
                "target_url": page_url,
                "expected": "no_crash_on_empty"
            })

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify browser back from '{page_name}' works",
                "category": "DeepFunctional",
                "type": "back_navigation",
                "target_url": page_url,
                "expected": "back_works"
            })

            test_id += 1
            tests.append({
                "id": f"TC_{test_id:03d}",
                "name": f"Verify '{page_name}' survives page reload",
                "category": "DeepFunctional",
                "type": "reload_test",
                "target_url": page_url,
                "expected": "page_loads_after_reload"
            })

        # ============================================
        # CATEGORY 9: Logout Test (always last)
        # ============================================

        test_id += 1
        tests.append({
            "id": f"TC_{test_id:03d}",
            "name": "Verify logout works",
            "category": "Logout",
            "type": "logout",
            "expected": "redirect_to_login"
        })

        self.generated_tests = tests

        log(f"Generated {len(tests)} test cases:")
        for t in tests:
            log(f"  [{t['id']}] [{t['category']}] {t['name']}")

        log("=" * 50)
        log(f"TEST CASE GENERATION COMPLETE: {len(tests)} tests")
        log("=" * 50)

        return tests


# from utils.logger import log
# import config


# class Planner:
#     def __init__(self, page):
#         self.page = page
#         self.discovered_pages = []
#         self.visited_urls = set()
#         self.page_map = []
#         self.generated_tests = []

#     def discover_links(self):
#         log("=" * 50)
#         log("DISCOVERY PHASE STARTED")
#         log("=" * 50)

#         links_found = []

#         for selector in config.NAV_SELECTORS:
#             try:
#                 elements = self.page.locator(selector).all()
#                 for element in elements:
#                     try:
#                         href = element.get_attribute("href") or ""
#                         text = element.inner_text().strip()

#                         if not text:
#                             text = element.get_attribute("aria-label") or "unknown"

#                         if self._should_skip(href, text):
#                             continue

#                         full_url = self._resolve_url(href)

#                         if full_url and full_url not in [l["url"] for l in links_found]:
#                             links_found.append({
#                                 "text": text,
#                                 "url": full_url,
#                                 "selector": selector
#                             })

#                     except Exception:
#                         continue
#             except Exception:
#                 continue

#         unique_links = []
#         seen_urls = set()
#         for link in links_found:
#             if link["url"] not in seen_urls:
#                 unique_links.append(link)
#                 seen_urls.add(link["url"])

#         log(f"Discovered {len(unique_links)} unique navigation links")
#         for i, link in enumerate(unique_links):
#             log(f"  [{i+1}] {link['text']} -> {link['url']}")

#         self.discovered_pages = unique_links
#         return unique_links

#     def discover_clickable_elements(self):
#         elements_found = {
#             "buttons": [],
#             "forms": [],
#             "tables": [],
#             "inputs": [],
#             "dropdowns": []
#         }

#         try:
#             buttons = self.page.locator("button").all()
#             for btn in buttons:
#                 try:
#                     text = btn.inner_text().strip()
#                     if text and len(text) < 50:
#                         elements_found["buttons"].append(text)
#                 except Exception:
#                     continue
#         except Exception:
#             pass

#         try:
#             forms = self.page.locator("form").count()
#             elements_found["forms"] = forms
#         except Exception:
#             elements_found["forms"] = 0

#         try:
#             tables = self.page.locator("table").count()
#             elements_found["tables"] = tables
#         except Exception:
#             elements_found["tables"] = 0

#         try:
#             inputs = self.page.locator("input:visible").all()
#             for inp in inputs:
#                 try:
#                     inp_type = inp.get_attribute("type") or "text"
#                     inp_name = inp.get_attribute("name") or inp.get_attribute("placeholder") or "unnamed"
#                     elements_found["inputs"].append(f"{inp_type}:{inp_name}")
#                 except Exception:
#                     continue
#         except Exception:
#             pass

#         try:
#             selects = self.page.locator("select").count()
#             elements_found["dropdowns"] = selects
#         except Exception:
#             elements_found["dropdowns"] = 0

#         return elements_found

#     def build_page_map(self, executor):
#         log("=" * 50)
#         log("PAGE MAPPING STARTED")
#         log("=" * 50)

#         base_url = self.page.url
#         self.visited_urls.add(base_url)

#         dashboard_elements = self.discover_clickable_elements()
#         self.page_map.append({
#             "page_name": "Dashboard",
#             "url": base_url,
#             "title": self.page.title(),
#             "elements": dashboard_elements
#         })
#         log(f"Mapped: Dashboard -> {base_url}")
#         self._log_elements(dashboard_elements)

#         for i, link in enumerate(self.discovered_pages):
#             if len(self.page_map) >= config.MAX_PAGES:
#                 log(f"Reached max pages limit ({config.MAX_PAGES})")
#                 break

#             if link["url"] in self.visited_urls:
#                 continue

#             log(f"\n--- Visiting [{i+1}/{len(self.discovered_pages)}]: {link['text']} ---")

#             try:
#                 self.page.goto(link["url"], wait_until="networkidle", timeout=15000)
#                 self.visited_urls.add(link["url"])
#                 self.page.wait_for_load_state("domcontentloaded")

#                 page_title = self.page.title()
#                 current_url = self.page.url

#                 elements = self.discover_clickable_elements()

#                 executor.take_screenshot(f"page_{i+1}_{self._safe_name(link['text'])}")

#                 self.page_map.append({
#                     "page_name": link["text"],
#                     "url": current_url,
#                     "title": page_title,
#                     "elements": elements
#                 })

#                 log(f"Mapped: {link['text']} -> {current_url}")
#                 self._log_elements(elements)

#                 sub_links = self._find_new_links()
#                 for sub in sub_links:
#                     if sub["url"] not in self.visited_urls and sub not in self.discovered_pages:
#                         self.discovered_pages.append(sub)
#                         log(f"  [NEW] Found sub-link: {sub['text']} -> {sub['url']}")

#             except Exception as e:
#                 log(f"Failed to visit: {link['text']} -> {str(e)[:100]}", level="ERROR")
#                 executor.take_screenshot(f"error_page_{i+1}")
#                 continue

#         log("=" * 50)
#         log(f"PAGE MAPPING COMPLETE: {len(self.page_map)} pages mapped")
#         log("=" * 50)

#         return self.page_map

#     def _find_new_links(self):
#         new_links = []
#         for selector in config.NAV_SELECTORS:
#             try:
#                 elements = self.page.locator(selector).all()
#                 for element in elements:
#                     try:
#                         href = element.get_attribute("href") or ""
#                         text = element.inner_text().strip()
#                         if not text:
#                             continue
#                         if self._should_skip(href, text):
#                             continue
#                         full_url = self._resolve_url(href)
#                         if full_url and full_url not in self.visited_urls:
#                             new_links.append({"text": text, "url": full_url, "selector": selector})
#                     except Exception:
#                         continue
#             except Exception:
#                 continue
#         return new_links

#     def _should_skip(self, href, text):
#         combined = (href + text).lower()
#         for keyword in config.SKIP_KEYWORDS:
#             if keyword in combined:
#                 return True
#         if href.startswith("http") and config.ALLOWED_DOMAIN not in href:
#             return True
#         if not href or href == "/" or href == "#":
#             return True
#         return False

#     def _resolve_url(self, href):
#         if not href:
#             return None
#         if href.startswith("http"):
#             return href
#         base = f"https://{config.ALLOWED_DOMAIN}"
#         if href.startswith("/"):
#             return base + href
#         return base + "/" + href

#     def _safe_name(self, text):
#         safe = "".join(c if c.isalnum() else "_" for c in text)
#         return safe[:30]

#     def _log_elements(self, elements):
#         log(f"  Buttons: {len(elements['buttons'])} -> {elements['buttons'][:5]}")
#         log(f"  Forms: {elements['forms']}")
#         log(f"  Tables: {elements['tables']}")
#         log(f"  Inputs: {len(elements['inputs'])}")
#         log(f"  Dropdowns: {elements['dropdowns']}")

#     def get_summary(self):
#         return {
#             "total_pages": len(self.page_map),
#             "total_links_found": len(self.discovered_pages),
#             "pages": [
#                 {
#                     "name": p["page_name"],
#                     "url": p["url"],
#                     "buttons": len(p["elements"]["buttons"]),
#                     "forms": p["elements"]["forms"],
#                     "tables": p["elements"]["tables"],
#                     "inputs": len(p["elements"]["inputs"]),
#                 }
#                 for p in self.page_map
#             ]
#         }

#     def generate_test_cases(self):
#         log("=" * 50)
#         log("TEST CASE GENERATION STARTED")
#         log("=" * 50)

#         test_id = 0
#         tests = []

#         # ============================================
#         # CATEGORY 1: Login Tests
#         # ============================================

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page loads",
#             "category": "Login",
#             "type": "page_load",
#             "target_url": config.APP_URL,
#             "action": "navigate",
#             "expected": "page_loads"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login with valid credentials",
#             "category": "Login",
#             "type": "login",
#             "action": "login",
#             "expected": "redirect_to_dashboard"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page has username field",
#             "category": "Login",
#             "type": "element_exists",
#             "target_url": config.APP_URL,
#             "selector": config.LOGIN_SELECTORS["username"],
#             "expected": "element_visible"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page has password field",
#             "category": "Login",
#             "type": "element_exists",
#             "target_url": config.APP_URL,
#             "selector": config.LOGIN_SELECTORS["password"],
#             "expected": "element_visible"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page has submit button",
#             "category": "Login",
#             "type": "element_exists",
#             "target_url": config.APP_URL,
#             "selector": config.LOGIN_SELECTORS["submit"],
#             "expected": "element_visible"
#         })

#         # ============================================
#         # CATEGORY 2: Navigation Tests (per page)
#         # ============================================

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page loads successfully",
#                 "category": "Navigation",
#                 "type": "page_load",
#                 "target_url": page_url,
#                 "action": "navigate",
#                 "expected": "page_loads"
#             })

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page has valid title",
#                 "category": "Navigation",
#                 "type": "title_check",
#                 "target_url": page_url,
#                 "expected": "title_not_empty"
#             })

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page has no console errors",
#                 "category": "Navigation",
#                 "type": "console_check",
#                 "target_url": page_url,
#                 "expected": "no_errors"
#             })

#         # ============================================
#         # CATEGORY 3: Button Tests
#         # ============================================

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             buttons = page_info["elements"].get("buttons", [])

#             for btn_text in buttons:
#                 if btn_text.lower() in ["logout", "log out", "sign out"]:
#                     continue

#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify '{btn_text}' button is clickable on '{page_name}'",
#                     "category": "Button",
#                     "type": "button_click",
#                     "target_url": page_url,
#                     "button_text": btn_text,
#                     "expected": "click_success"
#                 })

#         # ============================================
#         # CATEGORY 4: Input Field Tests
#         # ============================================

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             inputs = page_info["elements"].get("inputs", [])

#             for inp in inputs:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify input '{inp}' accepts text on '{page_name}'",
#                     "category": "Input",
#                     "type": "input_fill",
#                     "target_url": page_url,
#                     "input_info": inp,
#                     "expected": "input_accepts_text"
#                 })

#         # ============================================
#         # CATEGORY 5: Table Tests
#         # ============================================

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             tables = page_info["elements"].get("tables", 0)

#             if tables > 0:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify table has data on '{page_name}'",
#                     "category": "Table",
#                     "type": "table_check",
#                     "target_url": page_url,
#                     "expected": "table_has_rows"
#                 })

#         # ============================================
#         # CATEGORY 6: Cross-Navigation Tests
#         # ============================================

#         if len(self.page_map) >= 2:
#             for i in range(len(self.page_map) - 1):
#                 from_page = self.page_map[i]
#                 to_page = self.page_map[i + 1]

#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Navigate from '{from_page['page_name']}' to '{to_page['page_name']}'",
#                     "category": "CrossNav",
#                     "type": "cross_navigation",
#                     "from_url": from_page["url"],
#                     "to_url": to_page["url"],
#                     "to_name": to_page["page_name"],
#                     "expected": "navigation_success"
#                 })

#         # ============================================
#         # CATEGORY 7: Structure Tests
#         # ============================================

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page is not blank",
#                 "category": "Structure",
#                 "type": "not_blank",
#                 "target_url": page_url,
#                 "expected": "page_has_content"
#             })

#         # ============================================
#         # CATEGORY 8: Deep Functional Tests (NEW)
#         # ============================================

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             buttons = page_info["elements"].get("buttons", [])
#             inputs = page_info["elements"].get("inputs", [])
#             tables = page_info["elements"].get("tables", 0)

#             # Test: Search functionality
#             if inputs and any(b.lower() in ["search", "find", "go", "filter", "apply"] for b in buttons):
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify search/filter works on '{page_name}'",
#                     "category": "DeepFunctional",
#                     "type": "search_workflow",
#                     "target_url": page_url,
#                     "expected": "page_content_changes"
#                 })

#             # Test: Sort functionality
#             sort_buttons = [b for b in buttons if any(kw in b.lower() for kw in ["sort", "newest", "oldest", "a-z", "z-a", "first", "last", "ascending", "descending"])]
#             for sort_btn in sort_buttons:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify sort '{sort_btn}' changes content on '{page_name}'",
#                     "category": "DeepFunctional",
#                     "type": "sort_workflow",
#                     "target_url": page_url,
#                     "button_text": sort_btn,
#                     "expected": "content_changes_after_sort"
#                 })

#             # Test: Filter buttons (All, Active, etc.)
#             filter_buttons = [b for b in buttons if any(kw in b.lower() for kw in ["all", "active", "inactive", "pending", "completed", "open", "closed", "approved", "rejected"])]
#             for filter_btn in filter_buttons:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify filter '{filter_btn}' works on '{page_name}'",
#                     "category": "DeepFunctional",
#                     "type": "filter_workflow",
#                     "target_url": page_url,
#                     "button_text": filter_btn,
#                     "expected": "content_changes_after_filter"
#                 })

#             # Test: Form submission
#             if page_info["elements"].get("forms", 0) > 0 and inputs:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify form submission on '{page_name}'",
#                     "category": "DeepFunctional",
#                     "type": "form_workflow",
#                     "target_url": page_url,
#                     "expected": "form_submits_successfully"
#                 })

#             # Test: Page has proper error handling (no crash on empty actions)
#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' handles empty interactions gracefully",
#                 "category": "DeepFunctional",
#                 "type": "error_handling",
#                 "target_url": page_url,
#                 "expected": "no_crash_on_empty"
#             })

#             # Test: Back navigation works
#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify browser back from '{page_name}' works",
#                 "category": "DeepFunctional",
#                 "type": "back_navigation",
#                 "target_url": page_url,
#                 "expected": "back_works"
#             })

#             # Test: Page reload doesn't break
#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' survives page reload",
#                 "category": "DeepFunctional",
#                 "type": "reload_test",
#                 "target_url": page_url,
#                 "expected": "page_loads_after_reload"
#             })

#         # ============================================
#         # CATEGORY 9: Logout Test (always last)
#         # ============================================

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify logout works",
#             "category": "Logout",
#             "type": "logout",
#             "expected": "redirect_to_login"
#         })

#         self.generated_tests = tests

#         log(f"Generated {len(tests)} test cases:")
#         for t in tests:
#             log(f"  [{t['id']}] [{t['category']}] {t['name']}")

#         log("=" * 50)
#         log(f"TEST CASE GENERATION COMPLETE: {len(tests)} tests")
#         log("=" * 50)

#         return tests















# from utils.logger import log
# import config


# class Planner:
#     def __init__(self, page):
#         self.page = page
#         self.discovered_pages = []
#         self.visited_urls = set()
#         self.page_map = []
#         self.generated_tests = []

#     def discover_links(self):
#         log("=" * 50)
#         log("DISCOVERY PHASE STARTED")
#         log("=" * 50)

#         links_found = []

#         for selector in config.NAV_SELECTORS:
#             try:
#                 elements = self.page.locator(selector).all()
#                 for element in elements:
#                     try:
#                         href = element.get_attribute("href") or ""
#                         text = element.inner_text().strip()

#                         if not text:
#                             text = element.get_attribute("aria-label") or "unknown"

#                         if self._should_skip(href, text):
#                             continue

#                         full_url = self._resolve_url(href)

#                         if full_url and full_url not in [l["url"] for l in links_found]:
#                             links_found.append({
#                                 "text": text,
#                                 "url": full_url,
#                                 "selector": selector
#                             })

#                     except Exception:
#                         continue
#             except Exception:
#                 continue

#         unique_links = []
#         seen_urls = set()
#         for link in links_found:
#             if link["url"] not in seen_urls:
#                 unique_links.append(link)
#                 seen_urls.add(link["url"])

#         log(f"Discovered {len(unique_links)} unique navigation links")
#         for i, link in enumerate(unique_links):
#             log(f"  [{i+1}] {link['text']} -> {link['url']}")

#         self.discovered_pages = unique_links
#         return unique_links

#     def discover_clickable_elements(self):
#         elements_found = {
#             "buttons": [],
#             "forms": [],
#             "tables": [],
#             "inputs": [],
#             "dropdowns": []
#         }

#         try:
#             buttons = self.page.locator("button").all()
#             for btn in buttons:
#                 try:
#                     text = btn.inner_text().strip()
#                     if text and len(text) < 50:
#                         elements_found["buttons"].append(text)
#                 except Exception:
#                     continue
#         except Exception:
#             pass

#         try:
#             forms = self.page.locator("form").count()
#             elements_found["forms"] = forms
#         except Exception:
#             elements_found["forms"] = 0

#         try:
#             tables = self.page.locator("table").count()
#             elements_found["tables"] = tables
#         except Exception:
#             elements_found["tables"] = 0

#         try:
#             inputs = self.page.locator("input:visible").all()
#             for inp in inputs:
#                 try:
#                     inp_type = inp.get_attribute("type") or "text"
#                     inp_name = inp.get_attribute("name") or inp.get_attribute("placeholder") or "unnamed"
#                     elements_found["inputs"].append(f"{inp_type}:{inp_name}")
#                 except Exception:
#                     continue
#         except Exception:
#             pass

#         try:
#             selects = self.page.locator("select").count()
#             elements_found["dropdowns"] = selects
#         except Exception:
#             elements_found["dropdowns"] = 0

#         return elements_found

#     def build_page_map(self, executor):
#         log("=" * 50)
#         log("PAGE MAPPING STARTED")
#         log("=" * 50)

#         base_url = self.page.url
#         self.visited_urls.add(base_url)

#         dashboard_elements = self.discover_clickable_elements()
#         self.page_map.append({
#             "page_name": "Dashboard",
#             "url": base_url,
#             "title": self.page.title(),
#             "elements": dashboard_elements
#         })
#         log(f"Mapped: Dashboard -> {base_url}")
#         self._log_elements(dashboard_elements)

#         for i, link in enumerate(self.discovered_pages):
#             if len(self.page_map) >= config.MAX_PAGES:
#                 log(f"Reached max pages limit ({config.MAX_PAGES})")
#                 break

#             if link["url"] in self.visited_urls:
#                 continue

#             log(f"\n--- Visiting [{i+1}/{len(self.discovered_pages)}]: {link['text']} ---")

#             try:
#                 self.page.goto(link["url"], wait_until="networkidle", timeout=15000)
#                 self.visited_urls.add(link["url"])
#                 self.page.wait_for_load_state("domcontentloaded")

#                 page_title = self.page.title()
#                 current_url = self.page.url

#                 elements = self.discover_clickable_elements()

#                 executor.take_screenshot(f"page_{i+1}_{self._safe_name(link['text'])}")

#                 self.page_map.append({
#                     "page_name": link["text"],
#                     "url": current_url,
#                     "title": page_title,
#                     "elements": elements
#                 })

#                 log(f"Mapped: {link['text']} -> {current_url}")
#                 self._log_elements(elements)

#                 sub_links = self._find_new_links()
#                 for sub in sub_links:
#                     if sub["url"] not in self.visited_urls and sub not in self.discovered_pages:
#                         self.discovered_pages.append(sub)
#                         log(f"  [NEW] Found sub-link: {sub['text']} -> {sub['url']}")

#             except Exception as e:
#                 log(f"Failed to visit: {link['text']} -> {str(e)[:100]}", level="ERROR")
#                 executor.take_screenshot(f"error_page_{i+1}")
#                 continue

#         log("=" * 50)
#         log(f"PAGE MAPPING COMPLETE: {len(self.page_map)} pages mapped")
#         log("=" * 50)

#         return self.page_map

#     def _find_new_links(self):
#         new_links = []
#         for selector in config.NAV_SELECTORS:
#             try:
#                 elements = self.page.locator(selector).all()
#                 for element in elements:
#                     try:
#                         href = element.get_attribute("href") or ""
#                         text = element.inner_text().strip()
#                         if not text:
#                             continue
#                         if self._should_skip(href, text):
#                             continue
#                         full_url = self._resolve_url(href)
#                         if full_url and full_url not in self.visited_urls:
#                             new_links.append({"text": text, "url": full_url, "selector": selector})
#                     except Exception:
#                         continue
#             except Exception:
#                 continue
#         return new_links

#     def _should_skip(self, href, text):
#         combined = (href + text).lower()
#         for keyword in config.SKIP_KEYWORDS:
#             if keyword in combined:
#                 return True
#         if href.startswith("http") and config.ALLOWED_DOMAIN not in href:
#             return True
#         if not href or href == "/" or href == "#":
#             return True
#         return False

#     def _resolve_url(self, href):
#         if not href:
#             return None
#         if href.startswith("http"):
#             return href
#         base = f"https://{config.ALLOWED_DOMAIN}"
#         if href.startswith("/"):
#             return base + href
#         return base + "/" + href

#     def _safe_name(self, text):
#         safe = "".join(c if c.isalnum() else "_" for c in text)
#         return safe[:30]

#     def _log_elements(self, elements):
#         log(f"  Buttons: {len(elements['buttons'])} -> {elements['buttons'][:5]}")
#         log(f"  Forms: {elements['forms']}")
#         log(f"  Tables: {elements['tables']}")
#         log(f"  Inputs: {len(elements['inputs'])}")
#         log(f"  Dropdowns: {elements['dropdowns']}")

#     def get_summary(self):
#         return {
#             "total_pages": len(self.page_map),
#             "total_links_found": len(self.discovered_pages),
#             "pages": [
#                 {
#                     "name": p["page_name"],
#                     "url": p["url"],
#                     "buttons": len(p["elements"]["buttons"]),
#                     "forms": p["elements"]["forms"],
#                     "tables": p["elements"]["tables"],
#                     "inputs": len(p["elements"]["inputs"]),
#                 }
#                 for p in self.page_map
#             ]
#         }

#     def generate_test_cases(self):
#         log("=" * 50)
#         log("TEST CASE GENERATION STARTED")
#         log("=" * 50)

#         test_id = 0
#         tests = []

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page loads",
#             "category": "Login",
#             "type": "page_load",
#             "target_url": config.APP_URL,
#             "action": "navigate",
#             "expected": "page_loads"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login with valid credentials",
#             "category": "Login",
#             "type": "login",
#             "action": "login",
#             "expected": "redirect_to_dashboard"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page has username field",
#             "category": "Login",
#             "type": "element_exists",
#             "target_url": config.APP_URL,
#             "selector": config.LOGIN_SELECTORS["username"],
#             "expected": "element_visible"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page has password field",
#             "category": "Login",
#             "type": "element_exists",
#             "target_url": config.APP_URL,
#             "selector": config.LOGIN_SELECTORS["password"],
#             "expected": "element_visible"
#         })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify login page has submit button",
#             "category": "Login",
#             "type": "element_exists",
#             "target_url": config.APP_URL,
#             "selector": config.LOGIN_SELECTORS["submit"],
#             "expected": "element_visible"
#         })

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page loads successfully",
#                 "category": "Navigation",
#                 "type": "page_load",
#                 "target_url": page_url,
#                 "action": "navigate",
#                 "expected": "page_loads"
#             })

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page has valid title",
#                 "category": "Navigation",
#                 "type": "title_check",
#                 "target_url": page_url,
#                 "expected": "title_not_empty"
#             })

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page has no console errors",
#                 "category": "Navigation",
#                 "type": "console_check",
#                 "target_url": page_url,
#                 "expected": "no_errors"
#             })

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             buttons = page_info["elements"].get("buttons", [])

#             for btn_text in buttons:
#                 if btn_text.lower() in ["logout", "log out", "sign out"]:
#                     continue

#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify '{btn_text}' button is clickable on '{page_name}'",
#                     "category": "Button",
#                     "type": "button_click",
#                     "target_url": page_url,
#                     "button_text": btn_text,
#                     "expected": "click_success"
#                 })

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             inputs = page_info["elements"].get("inputs", [])

#             for inp in inputs:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify input '{inp}' accepts text on '{page_name}'",
#                     "category": "Input",
#                     "type": "input_fill",
#                     "target_url": page_url,
#                     "input_info": inp,
#                     "expected": "input_accepts_text"
#                 })

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]
#             tables = page_info["elements"].get("tables", 0)

#             if tables > 0:
#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Verify table has data on '{page_name}'",
#                     "category": "Table",
#                     "type": "table_check",
#                     "target_url": page_url,
#                     "expected": "table_has_rows"
#                 })

#         if len(self.page_map) >= 2:
#             for i in range(len(self.page_map) - 1):
#                 from_page = self.page_map[i]
#                 to_page = self.page_map[i + 1]

#                 test_id += 1
#                 tests.append({
#                     "id": f"TC_{test_id:03d}",
#                     "name": f"Navigate from '{from_page['page_name']}' to '{to_page['page_name']}'",
#                     "category": "CrossNav",
#                     "type": "cross_navigation",
#                     "from_url": from_page["url"],
#                     "to_url": to_page["url"],
#                     "to_name": to_page["page_name"],
#                     "expected": "navigation_success"
#                 })

#         for page_info in self.page_map:
#             page_name = page_info["page_name"]
#             page_url = page_info["url"]

#             test_id += 1
#             tests.append({
#                 "id": f"TC_{test_id:03d}",
#                 "name": f"Verify '{page_name}' page is not blank",
#                 "category": "Structure",
#                 "type": "not_blank",
#                 "target_url": page_url,
#                 "expected": "page_has_content"
#             })

#         test_id += 1
#         tests.append({
#             "id": f"TC_{test_id:03d}",
#             "name": "Verify logout works",
#             "category": "Logout",
#             "type": "logout",
#             "expected": "redirect_to_login"
#         })

#         self.generated_tests = tests

#         log(f"Generated {len(tests)} test cases:")
#         for t in tests:
#             log(f"  [{t['id']}] [{t['category']}] {t['name']}")

#         log("=" * 50)
#         log(f"TEST CASE GENERATION COMPLETE: {len(tests)} tests")
#         log("=" * 50)

#         return tests


# from utils.logger import log
# import config


# class Planner:
#     def __init__(self, page):
#         self.page = page
#         self.discovered_pages = []
#         self.visited_urls = set()
#         self.page_map = []
#         self.generated_tests = []


#     def discover_links(self):
#         """Find all navigable links on current page"""
#         log("=" * 50)
#         log("DISCOVERY PHASE STARTED")
#         log("=" * 50)

#         links_found = []

#         for selector in config.NAV_SELECTORS:
#             try:
#                 elements = self.page.locator(selector).all()
#                 for element in elements:
#                     try:
#                         href = element.get_attribute("href") or ""
#                         text = element.inner_text().strip()

#                         if not text:
#                             text = element.get_attribute("aria-label") or "unknown"

#                         # Skip unwanted links
#                         if self._should_skip(href, text):
#                             continue

#                         # Build full URL if relative
#                         full_url = self._resolve_url(href)

#                         if full_url and full_url not in [l["url"] for l in links_found]:
#                             links_found.append({
#                                 "text": text,
#                                 "url": full_url,
#                                 "selector": selector
#                             })

#                     except Exception:
#                         continue
#             except Exception:
#                 continue

#         # Deduplicate by URL
#         unique_links = []
#         seen_urls = set()
#         for link in links_found:
#             if link["url"] not in seen_urls:
#                 unique_links.append(link)
#                 seen_urls.add(link["url"])

#         log(f"Discovered {len(unique_links)} unique navigation links")
#         for i, link in enumerate(unique_links):
#             log(f"  [{i+1}] {link['text']} -> {link['url']}")

#         self.discovered_pages = unique_links
#         return unique_links

#     def discover_clickable_elements(self):
#         """Find buttons and interactive elements on current page"""
#         elements_found = {
#             "buttons": [],
#             "forms": [],
#             "tables": [],
#             "inputs": [],
#             "dropdowns": []
#         }

#         # Buttons
#         try:
#             buttons = self.page.locator("button").all()
#             for btn in buttons:
#                 try:
#                     text = btn.inner_text().strip()
#                     if text and len(text) < 50:
#                         elements_found["buttons"].append(text)
#                 except Exception:
#                     continue
#         except Exception:
#             pass

#         # Forms
#         try:
#             forms = self.page.locator("form").count()
#             elements_found["forms"] = forms
#         except Exception:
#             elements_found["forms"] = 0

#         # Tables
#         try:
#             tables = self.page.locator("table").count()
#             elements_found["tables"] = tables
#         except Exception:
#             elements_found["tables"] = 0

#         # Input fields
#         try:
#             inputs = self.page.locator("input:visible").all()
#             for inp in inputs:
#                 try:
#                     inp_type = inp.get_attribute("type") or "text"
#                     inp_name = inp.get_attribute("name") or inp.get_attribute("placeholder") or "unnamed"
#                     elements_found["inputs"].append(f"{inp_type}:{inp_name}")
#                 except Exception:
#                     continue
#         except Exception:
#             pass

#         # Dropdowns / Select
#         try:
#             selects = self.page.locator("select").count()
#             elements_found["dropdowns"] = selects
#         except Exception:
#             elements_found["dropdowns"] = 0

#         return elements_found

#     def build_page_map(self, executor):
#         """Visit each discovered page and collect metadata"""
#         log("=" * 50)
#         log("PAGE MAPPING STARTED")
#         log("=" * 50)

#         base_url = self.page.url
#         self.visited_urls.add(base_url)

#         # First map the current page (dashboard)
#         dashboard_elements = self.discover_clickable_elements()
#         self.page_map.append({
#             "page_name": "Dashboard",
#             "url": base_url,
#             "title": self.page.title(),
#             "elements": dashboard_elements
#         })
#         log(f"Mapped: Dashboard -> {base_url}")
#         self._log_elements(dashboard_elements)

#         # Visit each discovered link
#         for i, link in enumerate(self.discovered_pages):
#             if len(self.page_map) >= config.MAX_PAGES:
#                 log(f"Reached max pages limit ({config.MAX_PAGES})")
#                 break

#             if link["url"] in self.visited_urls:
#                 continue

#             log(f"\n--- Visiting [{i+1}/{len(self.discovered_pages)}]: {link['text']} ---")

#             try:
#                 # Navigate to page
#                 self.page.goto(link["url"], wait_until="networkidle", timeout=15000)
#                 self.visited_urls.add(link["url"])

#                 # Wait for content
#                 self.page.wait_for_load_state("domcontentloaded")

#                 # Collect page info
#                 page_title = self.page.title()
#                 current_url = self.page.url

#                 # Discover elements on this page
#                 elements = self.discover_clickable_elements()

#                 # Take screenshot
#                 executor.take_screenshot(f"page_{i+1}_{self._safe_name(link['text'])}")

#                 # Store in page map
#                 self.page_map.append({
#                     "page_name": link["text"],
#                     "url": current_url,
#                     "title": page_title,
#                     "elements": elements
#                 })

#                 log(f"Mapped: {link['text']} -> {current_url}")
#                 self._log_elements(elements)

#                 # Discover sub-links on this page (depth 2)
#                 sub_links = self._find_new_links()
#                 for sub in sub_links:
#                     if sub["url"] not in self.visited_urls and sub not in self.discovered_pages:
#                         self.discovered_pages.append(sub)
#                         log(f"  [NEW] Found sub-link: {sub['text']} -> {sub['url']}")

#             except Exception as e:
#                 log(f"Failed to visit: {link['text']} -> {str(e)[:100]}", level="ERROR")
#                 executor.take_screenshot(f"error_page_{i+1}")
#                 continue

#         log("=" * 50)
#         log(f"PAGE MAPPING COMPLETE: {len(self.page_map)} pages mapped")
#         log("=" * 50)

#         return self.page_map

#     def _find_new_links(self):
#         """Find links on current page that haven't been visited"""
#         new_links = []
#         for selector in config.NAV_SELECTORS:
#             try:
#                 elements = self.page.locator(selector).all()
#                 for element in elements:
#                     try:
#                         href = element.get_attribute("href") or ""
#                         text = element.inner_text().strip()
#                         if not text:
#                             continue
#                         if self._should_skip(href, text):
#                             continue
#                         full_url = self._resolve_url(href)
#                         if full_url and full_url not in self.visited_urls:
#                             new_links.append({"text": text, "url": full_url, "selector": selector})
#                     except Exception:
#                         continue
#             except Exception:
#                 continue
#         return new_links

#     def _should_skip(self, href, text):
#         """Check if link should be skipped"""
#         combined = (href + text).lower()
#         for keyword in config.SKIP_KEYWORDS:
#             if keyword in combined:
#                 return True

#         # Skip external links
#         if href.startswith("http") and config.ALLOWED_DOMAIN not in href:
#             return True

#         # Skip empty
#         if not href or href == "/" or href == "#":
#             return True

#         return False

#     def _resolve_url(self, href):
#         """Convert relative URL to absolute"""
#         if not href:
#             return None
#         if href.startswith("http"):
#             return href
#         base = f"https://{config.ALLOWED_DOMAIN}"
#         if href.startswith("/"):
#             return base + href
#         return base + "/" + href

#     def _safe_name(self, text):
#         """Convert text to safe filename"""
#         safe = "".join(c if c.isalnum() else "_" for c in text)
#         return safe[:30]

#     def _log_elements(self, elements):
#         """Log discovered elements"""
#         log(f"  Buttons: {len(elements['buttons'])} -> {elements['buttons'][:5]}")
#         log(f"  Forms: {elements['forms']}")
#         log(f"  Tables: {elements['tables']}")
#         log(f"  Inputs: {len(elements['inputs'])}")
#         log(f"  Dropdowns: {elements['dropdowns']}")

#     def get_summary(self):
#         """Return summary of discovered app"""
#         return {
#             "total_pages": len(self.page_map),
#             "total_links_found": len(self.discovered_pages),
#             "pages": [
#                 {
#                     "name": p["page_name"],
#                     "url": p["url"],
#                     "buttons": len(p["elements"]["buttons"]),
#                     "forms": p["elements"]["forms"],
#                     "tables": p["elements"]["tables"],
#                     "inputs": len(p["elements"]["inputs"]),
#                 }
#                 for p in self.page_map
#             ]
#         }