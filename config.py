
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

