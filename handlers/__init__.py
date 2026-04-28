from .start import register_start_handlers
from .admin import register_admin_handlers
from .free_orders import register_free_orders_handlers
from .paid_orders import register_paid_orders_handlers
from .mods import register_mods_handlers
from .support import register_support_handlers
from .rating import register_rating_handlers
from .language import register_language_handlers
from .broadcast import register_broadcast_handlers
from .admin_ban import register_ban_handlers

__all__ = [
    'register_start_handlers',
    'register_admin_handlers',
    'register_free_orders_handlers',
    'register_paid_orders_handlers',
    'register_mods_handlers',
    'register_support_handlers',
    'register_rating_handlers',
    'register_language_handlers',
    'register_broadcast_handlers',
    'register_ban_handlers'
]