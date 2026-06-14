
from playwright.sync_api import sync_playwright
import config

_playwright = None
_browser = None

def launch_browser():
    global _playwright, _browser
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=config.HEADLESS,
        slow_mo=config.SLOW_MO,
        channel="msedge",
        args=["--ignore-certificate-errors"]
    )
    context = _browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(config.TIMEOUT)
    return page

def close_browser():
    global _playwright, _browser
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
# from playwright.sync_api import sync_playwright
# import config

# _playwright = None
# _browser = None

# def launch_browser():
#     global _playwright, _browser
#     _playwright = sync_playwright().start()
#     _browser = _playwright.chromium.launch(
#         headless=config.HEADLESS,
#         slow_mo=config.SLOW_MO,
#         channel="chrome",
#         args=["--ignore-certificate-errors"]
#     )
#     context = _browser.new_context(ignore_https_errors=True)
#     page = context.new_page()
#     page.set_default_timeout(config.TIMEOUT)
#     return page

# def close_browser():
#     global _playwright, _browser
#     if _browser:
#         _browser.close()
#     if _playwright:
#         _playwright.stop()



# from playwright.sync_api import sync_playwright
# import config

# _playwright = None
# _browser = None

# def launch_browser():
#     global _playwright, _browser
#     _playwright = sync_playwright().start()
#     _browser = _playwright.chromium.launch(
#         headless=config.HEADLESS,
#         slow_mo=config.SLOW_MO
#     )
#     context = _browser.new_context()
#     page = context.new_page()
#     page.set_default_timeout(config.TIMEOUT)
#     return page

# def close_browser():
#     global _playwright, _browser
#     if _browser:
#         _browser.close()
#     if _playwright:
#         _playwright.stop()

        