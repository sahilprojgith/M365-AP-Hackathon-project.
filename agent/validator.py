from utils.logger import log
import config

class Validator:
    def __init__(self, page):
        self.page = page

    def validate_login(self):
        log("=" * 50)
        log("LOGIN VALIDATION STARTED")
        log("=" * 50)

        results = {
            "url_check": False,
            "element_check": False,
            "login_form_gone": False,
            "overall": False
        }

        current_url = self.page.url.lower()

        # Strategy 1: URL should NOT contain login keywords
        url_clean = True
        for keyword in config.LOGIN_SUCCESS["url_must_not_contain"]:
            if keyword in current_url:
                url_clean = False
                log(f"URL still contains '{keyword}': {current_url}", level="WARN")
                break

        if url_clean:
            log(f"URL check PASSED: {current_url}")
            results["url_check"] = True
        else:
            log(f"URL check FAILED: {current_url}", level="WARN")

        # Strategy 2: Dashboard element should exist
        element_found = False
        for selector in config.LOGIN_SUCCESS["elements_should_exist"]:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=3000):
                    log(f"Element check PASSED: found '{selector}'")
                    element_found = True
                    break
            except Exception:
                continue

        results["element_check"] = element_found
        if not element_found:
            log("Element check FAILED: no dashboard element found", level="WARN")

        # Strategy 3: Login form should be GONE
        login_form_gone = True
        for selector in config.LOGIN_SELECTORS["password"]:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=2000):
                    login_form_gone = False
                    log(f"Login form still visible: '{selector}'", level="WARN")
                    break
            except Exception:
                continue

        results["login_form_gone"] = login_form_gone
        if login_form_gone:
            log("Login form check PASSED: password field no longer visible")
        else:
            log("Login form check FAILED: login form still showing", level="WARN")

        # Overall: login form must be gone AND (url changed OR element found)
        results["overall"] = results["login_form_gone"] and (results["url_check"] or results["element_check"])

        if results["overall"]:
            log("LOGIN VALIDATION: PASSED", level="INFO")
        else:
            log("LOGIN VALIDATION: FAILED", level="ERROR")

        return results