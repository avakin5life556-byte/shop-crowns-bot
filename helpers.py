import re
import json
from datetime import datetime
from config import TIMEZONE

def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input - remove dangerous characters and limit length
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove dangerous special characters
    text = re.sub(r'[<>{}()\[\]\\;`]', '', text)
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_username(username: str) -> bool:
    """
    Validate Telegram username format
    
    Args:
        username: Username to validate (without @)
    
    Returns:
        True if valid, False otherwise
    """
    if not username:
        return True  # Username is optional
    
    pattern = r'^[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, username))

def safe_json_loads(data: str) -> dict:
    """
    Safely load JSON data
    
    Args:
        data: JSON string to parse
    
    Returns:
        Parsed dictionary or empty dict on error
    """
    try:
        if isinstance(data, str):
            return json.loads(data)
        return data
    except (json.JSONDecodeError, TypeError):
        return {}

def safe_json_dumps(data: dict) -> str:
    """
    Safely dump dictionary to JSON
    
    Args:
        data: Dictionary to serialize
    
    Returns:
        JSON string or "{}" on error
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"

def is_rate_limited(user_id: int, action: str, limit: int = 5, window: int = 60) -> bool:
    """
    Check if user is rate limited for an action
    
    Args:
        user_id: User ID to check
        action: Action name (e.g., 'change_name', 'paid_order')
        limit: Maximum allowed actions in window
        window: Time window in seconds
    
    Returns:
        True if rate limited, False otherwise
    """
    from collections import defaultdict
    import time
    
    # Storage for rate limits
    if not hasattr(is_rate_limited, '_storage'):
        is_rate_limited._storage = defaultdict(list)
    
    key = f"{user_id}:{action}"
    now = time.time()
    
    # Clean old entries
    is_rate_limited._storage[key] = [t for t in is_rate_limited._storage[key] if now - t < window]
    
    if len(is_rate_limited._storage[key]) >= limit:
        return True
    
    is_rate_limited._storage[key].append(now)
    return False

def format_datetime(dt) -> str:
    """Format datetime to string"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_date_arabic(dt) -> str:
    """Format date in Arabic"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    
    days = {
        0: 'الإثنين', 1: 'الثلاثاء', 2: 'الأربعاء', 3: 'الخميس',
        4: 'الجمعة', 5: 'السبت', 6: 'الأحد'
    }
    months = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }
    
    return f"{days[dt.weekday()]}، {dt.day} {months[dt.month]} {dt.year}"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def extract_user_mention(username: str) -> str:
    """Extract user mention from username"""
    if username and username != 'No username':
        return f"@{username}"
    return "لا يوجد"

def get_user_display_name(full_name: str, username: str = None) -> str:
    """Get user display name with username if available"""
    if username and username != 'No username':
        return f"{full_name} (@{username})"
    return full_name

def generate_random_id(length: int = 8) -> str:
    """Generate random ID"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def parse_command_args(text: str) -> tuple:
    """Parse command arguments"""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None, None
    return parts[0], parts[1]

def get_current_time() -> str:
    """Get current time as ISO string"""
    return datetime.now(TIMEZONE).isoformat()

def get_current_timestamp() -> int:
    """Get current Unix timestamp"""
    return int(datetime.now(TIMEZONE).timestamp())

def is_valid_order_data(data: dict) -> bool:
    """Validate order data structure"""
    required_keys = ['new_name', 'email', 'password'] if 'new_name' in data else ['photo_id', 'email', 'password']
    return all(k in data for k in required_keys)