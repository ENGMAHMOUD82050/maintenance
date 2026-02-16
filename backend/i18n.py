# backend/i18n.py
# English-only (temporary). Arabic disabled.

def get_lang():
    # Force English always
    return "en"

# Basic translations (expand later if needed)
_EN = {
    "language": "Language",
    "logout": "Logout",
    "dashboard": "Dashboard",
    "create_ticket": "Create Ticket",
    "locations": "Locations",
    "users": "Users",
    "kpi": "Monthly KPI",
}

def t(key: str) -> str:
    # Return English label if found; otherwise return key itself
    return _EN.get(key, key)
