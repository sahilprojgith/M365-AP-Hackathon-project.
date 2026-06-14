
# Application under test
APP_URL = "some application"
USERNAME = "id"
PASSWORD = "password"

# Browser settings
HEADLESS = False
SLOW_MO = 500
TIMEOUT = 30000

# Output paths
REPORT_DIR = "reports"
SCREENSHOT_DIR = "screenshots"

# Login selectors (agent tries each dynamically)
LOGIN_SELECTORS = {
    "username": [
        'input[name="username"]',
        'input[name="userId"]',
        'input[name="user"]',
        'input[name="login"]',
        'input[name="email"]',
        'input[type="text"]',
        'input[type="email"]',
        '#username',
        '#userId',
        '#user',
        '[placeholder*="user" i]',
        '[placeholder*="email" i]',
        '[placeholder*="id" i]',
        '[placeholder*="login" i]',
    ],
    "password": [
        'input[name="password"]',
        'input[name="pass"]',
        'input[type="password"]',
        '#password',
        '[placeholder*="password" i]',
    ],
    "submit": [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Sign in")',
        'button:has-text("Sign In")',
        'button:has-text("Log in")',
        'button:has-text("Log In")',
        'button:has-text("Submit")',
        'button:has-text("Continue")',
        'button:has-text("Enter")',
        '[class*="login" i] button',
        '[class*="submit" i]',
    ]
}

# Login success indicators
LOGIN_SUCCESS = {
    "url_must_not_contain": ["login", "signin", "auth"],
    "elements_should_exist": [
        'a:has-text("Logout")',
        'a:has-text("Log out")',
        'button:has-text("Logout")',
        '[class*="dashboard"]',
        '[class*="home"]',
        '[class*="sidebar"]',
        '[class*="navbar"]',
        '[class*="menu"]',
        '[class*="header"]',
        'nav',
    ]
}
# Navigation settings
MAX_DEPTH = 3                    # how deep to explore
MAX_PAGES = 50                   # stop after this many pages

# Links to AVOID (agent will skip these)
SKIP_KEYWORDS = [
    "logout", "log-out", "log_out", "signout", "sign-out",
    "sign_out", "exit", "mailto:", "tel:", "javascript:",
    "#", "void(0)"
]

# Only follow links within this domain
ALLOWED_DOMAIN = "meri marzi"

# Navigation selectors (agent tries these to find menus)
NAV_SELECTORS = [
    'nav a',
    'aside a',
    '[class*="sidebar"] a',
    '[class*="menu"] a',
    '[class*="nav"] a',
    '[class*="drawer"] a',
    '[role="navigation"] a',
    '[role="menu"] a',
    '[role="menuitem"]',
    'ul li a',
    'header a',
    '.MuiDrawer-root a',
    '.MuiList-root a',
    '.MuiListItem-root',
    '[class*="list"] a',
]


# LLM Configuration

# LLM Configuration (Azure OpenAI)
LLM_PROVIDER = "azure"
LLM_API_KEY = "key"
LLM_ENDPOINT = "lund"
LLM_MODEL = "gpt-5.2"
LLM_API_VERSION = "2024-12-01-preview"


from utils.browser import launch_browser, close_browser
from utils.logger import log
from agent.brain import Brain


def run():
    page = launch_browser()

    try:
        agent = Brain(page)
        agent.run()
    except Exception as e:
        log(f"Agent crashed: {str(e)}", level="ERROR")
    finally:
        close_browser()
        log("Browser closed")


if __name__ == "__main__":
    run()


# import json
# import os
# from utils.browser import launch_browser, close_browser
# from utils.logger import log
# from agent.executor import Executor
# from agent.validator import Validator
# from agent.planner import Planner
# import config

# def run():
#     log("=" * 50)
#     log("APA TESTING AGENT STARTED")
#     log("=" * 50)
#     log(f"Target: {config.APP_URL}")

#     # Step 1: Launch browser
#     page = launch_browser()
#     log("Browser launched")

#     # Step 2: Initialize agent modules
#     executor = Executor(page)
#     validator = Validator(page)
#     planner = Planner(page)

#     # Step 3: Login
#     login_executed = executor.login()

#     if not login_executed:
#         log("Agent stopped: login execution failed", level="ERROR")
#         executor.take_screenshot("login_failed_final")
#         close_browser()
#         return

#     # Step 4: Validate login
#     login_result = validator.validate_login()

#     if not login_result["overall"]:
#         log("Agent stopped: login validation failed", level="ERROR")
#         executor.take_screenshot("login_validation_failed")
#         close_browser()
#         return

#     log(f"Logged in at: {executor.get_current_url()}")
#     executor.take_screenshot("03_dashboard")

#     # Step 5: Discover navigation links
#     links = planner.discover_links()

#     if not links:
#         log("No navigation links found. Agent stopping.", level="WARN")
#         close_browser()
#         return

#     # Step 6: Build page map (visit all pages)
#     page_map = planner.build_page_map(executor)

#     # Step 7: Save page map as JSON
#     os.makedirs(config.REPORT_DIR, exist_ok=True)
#     summary = planner.get_summary()

#     with open(f"{config.REPORT_DIR}/page_map.json", "w") as f:
#         json.dump(summary, f, indent=2)
#     log(f"Page map saved to {config.REPORT_DIR}/page_map.json")

#     # Print summary
#     log("=" * 50)
#     log("APP DISCOVERY SUMMARY")
#     log("=" * 50)
#     log(f"Total pages mapped: {summary['total_pages']}")
#     log(f"Total links found: {summary['total_links_found']}")
#     for p in summary["pages"]:
#         log(f"  {p['name']}: buttons={p['buttons']}, forms={p['forms']}, tables={p['tables']}, inputs={p['inputs']}")

#     log("=" * 50)
#     log("PHASE 3 COMPLETE: Navigation + Discovery done")
#     log("=" * 50)

#     # Cleanup
#     close_browser()
#     log("Browser closed")

# if __name__ == "__main__":
#     run()


# # from utils.browser import launch_browser, close_browser
# # from utils.logger import log
# # import config

# # def run():
# #     log("APA Testing Agent starting...")
# #     log(f"Target: {config.APP_URL}")

# #     # Step 1: Launch browser
# #     page = launch_browser()
# #     log("Browser launched")

# #     # Step 2: Navigate to target
# #     page.goto(config.APP_URL)
# #     log(f"Navigated to: {page.url}")
# #     log(f"Page title: {page.title()}")

# #     # Step 3: Take screenshot as proof
# #     page.screenshot(path=f"{config.SCREENSHOT_DIR}/landing_page.png")
# #     log("Screenshot saved: landing_page.png")

# #     # Cleanup
# #     close_browser()
# #     log("Browser closed")
# #     log("Phase 1 complete")

# # if __name__ == "__main__":
# #     run()