import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import TIMEZONE, ORDER_TIMEOUT_MINUTES, ADMIN_ID

class TimeoutManager:
    """
    Unified Timeout Manager for all orders
    Handles automatic timeout for pending orders
    """
    
    def __init__(self):
        self._timeouts: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._bot = None

    def set_bot(self, bot):
        """Set bot instance for sending messages"""
        self._bot = bot

    async def set_timeout(self, order_number: str, user_id: int, bot, timeout_minutes: int = ORDER_TIMEOUT_MINUTES):
        """
        Set a timeout for an order
        
        Args:
            order_number: The order number to monitor
            user_id: The user ID who placed the order
            bot: Bot instance for sending messages
            timeout_minutes: Timeout duration in minutes
        """
        async with self._lock:
            # Cancel existing timeout if any
            await self.cancel_timeout(order_number)

            # Create timeout task
            async def timeout_callback():
                await asyncio.sleep(timeout_minutes * 60)
                await self._handle_timeout(order_number, user_id)

            task = asyncio.create_task(timeout_callback())
            
            self._timeouts[order_number] = {
                'task': task,
                'user_id': user_id,
                'expires_at': datetime.now(TIMEZONE) + timedelta(minutes=timeout_minutes),
                'timeout_minutes': timeout_minutes
            }

    async def cancel_timeout(self, order_number: str) -> bool:
        """
        Cancel a timeout for an order
        
        Args:
            order_number: The order number to cancel timeout for
            
        Returns:
            True if timeout was cancelled, False if not found
        """
        async with self._lock:
            if order_number in self._timeouts:
                self._timeouts[order_number]['task'].cancel()
                del self._timeouts[order_number]
                return True
            return False

    async def _handle_timeout(self, order_number: str, user_id: int):
        """
        Handle timeout expiration
        """
        from database import db
        
        # Update order status in database
        db.update_order_status(order_number, 'timeout')
        
        # Log timeout action
        db.log_admin_action(None, 'order_timeout', user_id, order_number, f'تجاوز {ORDER_TIMEOUT_MINUTES} دقيقة')
        
        # Get user language for localized message
        lang = db.get_user_language(user_id)
        timeout_message = (
            f"⏰ **لم يتم قبول طلبك حالياً**\n\n"
            f"📌 رقم الطلب: {order_number}\n"
            f"🕐 الطلب تجاوز {ORDER_TIMEOUT_MINUTES} دقيقة بدون معالجة\n\n"
            f"يمكنك إعادة تقديم الطلب مرة أخرى."
            if lang == 'ar' else
            f"⏰ **Your request has timed out**\n\n"
            f"📌 Order number: {order_number}\n"
            f"🕐 Request exceeded {ORDER_TIMEOUT_MINUTES} minutes without processing\n\n"
            f"You can submit your request again."
        )
        
        # Send message to user
        if self._bot:
            await self._bot.send_message(user_id, timeout_message, parse_mode='Markdown')
            
            # Notify admin
            await self._bot.send_message(
                ADMIN_ID,
                f"⏰ **طلب منتهي المهلة**\n\n"
                f"📌 رقم الطلب: {order_number}\n"
                f"👤 المستخدم: {user_id}\n"
                f"🕐 تجاوز {ORDER_TIMEOUT_MINUTES} دقيقة\n"
                f"📅 الوقت: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode='Markdown'
            )
        
        # Remove from active timeouts
        async with self._lock:
            if order_number in self._timeouts:
                del self._timeouts[order_number]

    async def get_remaining_time(self, order_number: str) -> int:
        """
        Get remaining time in minutes for a timeout
        
        Args:
            order_number: The order number to check
            
        Returns:
            Remaining time in minutes, 0 if no timeout
        """
        if order_number in self._timeouts:
            remaining = (self._timeouts[order_number]['expires_at'] - datetime.now(TIMEZONE)).total_seconds()
            return max(0, int(remaining / 60))
        return 0

    def has_active_timeout(self, order_number: str) -> bool:
        """
        Check if an order has an active timeout
        
        Args:
            order_number: The order number to check
            
        Returns:
            True if timeout exists, False otherwise
        """
        return order_number in self._timeouts

    def get_all_active_timeouts(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active timeouts
        
        Returns:
            Dictionary of active timeouts
        """
        return self._timeouts.copy()

    async def clear_all_timeouts(self):
        """
        Clear all active timeouts (for shutdown)
        """
        async with self._lock:
            for order_number in list(self._timeouts.keys()):
                await self.cancel_timeout(order_number)

    async def refresh_timeout(self, order_number: str, user_id: int, bot, extra_minutes: int = 10):
        """
        Refresh an existing timeout by adding extra minutes
        
        Args:
            order_number: The order number to refresh
            user_id: The user ID
            bot: Bot instance
            extra_minutes: Extra minutes to add
        """
        if order_number in self._timeouts:
            current_remaining = await self.get_remaining_time(order_number)
            new_timeout = max(current_remaining + extra_minutes, extra_minutes)
            await self.cancel_timeout(order_number)
            await self.set_timeout(order_number, user_id, bot, new_timeout)


# Singleton instance
timeout_manager = TimeoutManager()