import os
import pytz

# ======== Bot Configuration ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_IDS = [ADMIN_ID]

# ======== Timezone ========
TIMEZONE = pytz.timezone('Africa/Cairo')

# ======== Timeout Settings ========
ORDER_TIMEOUT_MINUTES = 30
QUEUE_CHECK_INTERVAL = 10

# ======== Database ========
DATABASE_PATH = "database.db"

# ======== Logging ========
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ======== Mods Links ========
MOD_LINKS = {
    "sky": "test",
    "bull": "test",
    "bull_alt": "test",
    "gold": "test"
}