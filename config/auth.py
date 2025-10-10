"""
Authentication configuration for BotCamp Medical
Contains admin and super-admin access codes
"""

# Admin access codes (can be changed by super admin)
ADMIN_CODES = {
    "admin123": "Admin User 1",
    "medadmin": "Medical Admin",
    "quizmaster": "Quiz Master"
}

# Super Admin access code (should be kept secure)
SUPER_ADMIN_CODE = "superadmin2024"

# Default super admin Telegram ID (set this to your Telegram ID)
DEFAULT_SUPER_ADMIN_ID = 1769515855  # Replace with actual super admin ID

def verify_admin_code(code: str) -> bool:
    """Verify if the provided code is a valid admin code"""
    return code in ADMIN_CODES

def verify_super_admin_code(code: str) -> bool:
    """Verify if the provided code is the super admin code"""
    return code == SUPER_ADMIN_CODE

def get_admin_name(code: str) -> str:
    """Get the admin name for a given code"""
    return ADMIN_CODES.get(code, "Unknown Admin")

def add_admin_code(code: str, name: str) -> bool:
    """Add a new admin code (super admin only)"""
    if code not in ADMIN_CODES:
        ADMIN_CODES[code] = name
        return True
    return False

def remove_admin_code(code: str) -> bool:
    """Remove an admin code (super admin only)"""
    if code in ADMIN_CODES:
        del ADMIN_CODES[code]
        return True
    return False

def list_admin_codes() -> dict:
    """List all admin codes (super admin only)"""
    return ADMIN_CODES.copy()
