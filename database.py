import sqlite3
import threading
from datetime import datetime
from config import TIMEZONE, DATABASE_PATH
import logging

logger = logging.getLogger(__name__)

class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize database connection and create tables"""
        try:
            self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self._create_tables()
            self._create_indexes()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _create_tables(self):
        """Create all tables if not exist"""
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                language TEXT DEFAULT 'ar',
                country TEXT DEFAULT 'غير معروف',
                is_banned INTEGER DEFAULT 0,
                registered_at TEXT,
                last_active TEXT
            )
        ''')

        # Orders table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE,
                user_id INTEGER,
                order_type TEXT,
                order_data TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Tickets table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT UNIQUE,
                user_id INTEGER,
                ticket_type TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT,
                closed_at TEXT,
                assigned_admin INTEGER
            )
        ''')

        # Ticket messages
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                sender_id INTEGER,
                message TEXT,
                created_at TEXT,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            )
        ''')

        # Chat sessions
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                admin_id INTEGER,
                ticket_id INTEGER,
                status TEXT DEFAULT 'active',
                started_at TEXT,
                ended_at TEXT
            )
        ''')

        # Admin logs
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                target_user INTEGER,
                order_number TEXT,
                details TEXT,
                timestamp TEXT
            )
        ''')
        
        # Banned users
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                reason TEXT,
                date TEXT,
                banned_by INTEGER
            )
        ''')

        # Ratings
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rating INTEGER,
                rating_type TEXT,
                comment TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        self.conn.commit()

    def _create_indexes(self):
        """Create indexes for better query performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_id ON users(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_lang ON users(language)",
            "CREATE INDEX IF NOT EXISTS idx_users_banned ON users(is_banned)",
            "CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number)",
            "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
            "CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_status ON chat_sessions(status)",
            "CREATE INDEX IF NOT EXISTS idx_admin_logs_timestamp ON admin_logs(timestamp)",
        ]
        
        for index in indexes:
            try:
                self.cursor.execute(index)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
        
        self.conn.commit()
        logger.info("Database indexes created successfully")

    # ========== User Methods ==========
    def register_user(self, user_id: int, full_name: str, username: str, language: str = 'ar') -> bool:
        """Register a new user"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, full_name, username, language, country, registered_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, full_name, username, language, self._get_user_country(user_id), now, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to register user {user_id}: {e}")
            return False

    def _get_user_country(self, user_id: int) -> str:
        """Get user country (placeholder - can integrate with IP API)"""
        return 'مصر'

    def get_user_language(self, user_id: int) -> str:
        """Get user's language preference"""
        try:
            self.cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            return row['language'] if row else 'ar'
        except Exception as e:
            logger.error(f"Failed to get user language for {user_id}: {e}")
            return 'ar'

    def set_user_language(self, user_id: int, language: str) -> bool:
        """Set user's language preference"""
        try:
            self.cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set user language for {user_id}: {e}")
            return False

    def update_last_active(self, user_id: int) -> bool:
        """Update user's last active timestamp"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update last active for {user_id}: {e}")
            return False

    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            self.cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            return row and row['is_banned'] == 1
        except Exception as e:
            logger.error(f"Failed to check ban status for {user_id}: {e}")
            return False

    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
            return False

    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to unban user {user_id}: {e}")
            return False

    def get_user_info(self, user_id: int):
        """Get user information"""
        try:
            self.cursor.execute('SELECT full_name, username, language, country, is_banned FROM users WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            if row:
                return {
                    'name': row['full_name'],
                    'username': row['username'],
                    'lang': row['language'],
                    'country': row['country'],
                    'is_banned': row['is_banned']
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return None

    # ========== Order Methods ==========
    def generate_order_number(self) -> str:
        """Generate unique order number"""
        return f"SC-{datetime.now(TIMEZONE).strftime('%Y%m%d%H%M%S')}"

    def create_order(self, user_id: int, order_type: str, order_data: str) -> str:
        """Create a new order"""
        try:
            order_number = self.generate_order_number()
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT INTO orders (order_number, user_id, order_type, order_data, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            ''', (order_number, user_id, order_type, order_data, now, now))
            self.conn.commit()
            logger.info(f"Order created: {order_number} for user {user_id}")
            return order_number
        except Exception as e:
            logger.error(f"Failed to create order for user {user_id}: {e}")
            return None

    def get_order(self, order_number: str):
        """Get order by number"""
        try:
            self.cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get order {order_number}: {e}")
            return None

    def update_order_status(self, order_number: str, status: str) -> bool:
        """Update order status"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('UPDATE orders SET status = ?, updated_at = ? WHERE order_number = ?',
                               (status, now, order_number))
            self.conn.commit()
            logger.info(f"Order {order_number} status updated to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update order {order_number}: {e}")
            return False

    def get_pending_orders(self, limit: int = 50):
        """Get pending orders"""
        try:
            self.cursor.execute('''
                SELECT * FROM orders WHERE status = 'pending' OR status = 'processing'
                ORDER BY created_at ASC LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get pending orders: {e}")
            return []

    # ========== Ticket Methods ==========
    def generate_ticket_number(self) -> str:
        """Generate unique ticket number"""
        return f"TCK-{datetime.now(TIMEZONE).strftime('%Y%m%d%H%M%S')}"

    def create_ticket(self, user_id: int, ticket_type: str, message: str):
        """Create a support ticket"""
        try:
            ticket_number = self.generate_ticket_number()
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT INTO tickets (ticket_number, user_id, ticket_type, status, created_at)
                VALUES (?, ?, ?, 'open', ?)
            ''', (ticket_number, user_id, ticket_type, now))
            ticket_id = self.cursor.lastrowid
            
            self.cursor.execute('''
                INSERT INTO ticket_messages (ticket_id, sender_id, message, created_at)
                VALUES (?, ?, ?, ?)
            ''', (ticket_id, user_id, message, now))
            self.conn.commit()
            logger.info(f"Ticket created: {ticket_number} for user {user_id}")
            return ticket_number, ticket_id
        except Exception as e:
            logger.error(f"Failed to create ticket for user {user_id}: {e}")
            return None, None

    def add_ticket_message(self, ticket_id: int, sender_id: int, message: str) -> bool:
        """Add message to ticket"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT INTO ticket_messages (ticket_id, sender_id, message, created_at)
                VALUES (?, ?, ?, ?)
            ''', (ticket_id, sender_id, message, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add ticket message: {e}")
            return False

    def get_active_chat(self, user_id: int):
        """Get active chat session for user"""
        try:
            self.cursor.execute('''
                SELECT * FROM chat_sessions WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get active chat for {user_id}: {e}")
            return None

    def create_chat_session(self, user_id: int, admin_id: int, ticket_id: int) -> int:
        """Create a new chat session"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT INTO chat_sessions (user_id, admin_id, ticket_id, status, started_at)
                VALUES (?, ?, ?, 'active', ?)
            ''', (user_id, admin_id, ticket_id, now))
            session_id = self.cursor.lastrowid
            self.conn.commit()
            return session_id
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            return None

    def close_chat_session(self, session_id: int) -> bool:
        """Close a chat session"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                UPDATE chat_sessions SET status = 'closed', ended_at = ? WHERE id = ?
            ''', (now, session_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to close chat session {session_id}: {e}")
            return False

    def close_ticket(self, ticket_number: str) -> bool:
        """Close a ticket"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                UPDATE tickets SET status = 'closed', closed_at = ? WHERE ticket_number = ?
            ''', (now, ticket_number))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to close ticket {ticket_number}: {e}")
            return False

    # ========== Admin Logs ==========
    def log_admin_action(self, admin_id: int, action: str, target_user: int = None, 
                         order_number: str = None, details: str = None) -> bool:
        """Log admin action"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT INTO admin_logs (admin_id, action, target_user, order_number, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (admin_id, action, target_user, order_number, details, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            return False

    # ========== Stats Methods ==========
    def get_all_users(self):
        """Get all active users"""
        try:
            self.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []

    def get_stats(self) -> dict:
        """Get bot statistics"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 0')
            active = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
            banned = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM orders')
            total_orders = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"')
            pending_orders = self.cursor.fetchone()[0]
            
            return {
                'active': active,
                'banned': banned,
                'total_orders': total_orders,
                'pending_orders': pending_orders
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'active': 0, 'banned': 0, 'total_orders': 0, 'pending_orders': 0}

    # ========== Rating Methods ==========
    def save_rating(self, user_id: int, rating: int, rating_type: str = 'bot', comment: str = '') -> bool:
        """Save user rating"""
        try:
            now = datetime.now(TIMEZONE).isoformat()
            self.cursor.execute('''
                INSERT INTO ratings (user_id, rating, rating_type, comment, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, rating, rating_type, comment, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save rating for user {user_id}: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# Singleton instance
db = Database()