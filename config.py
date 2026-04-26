BOT_TOKEN = "8721060352:AAH8hLCMGWCjk_hwCCwsphLedmT-Em11EoY"
ADMIN_IDS = [7950038145]  # твой Telegram ID

# Только два канала (приватные, инвайт-ссылки)
REQUIRED_CHANNELS = [
    {"name": "FL Osint", "url": "https://t.me/+TSQqyiX1DPVlY2Qy"},
    {"name": "psychos", "url": "https://t.me/+W4dtlB6y511hM2Zi"}
]

POSTGRES_DSN = "postgresql://user:pass@localhost/fl_bot"
ELASTIC_HOST = "http://localhost:9200"
ELASTIC_INDEX = "osint_data"

PRICES = {
    2: 20,
    4: 50,
    15: 200,
    30: 500,
    50: 1000,
    120: 3000,
    600: 20000
}

CRYPTO_BOT_TOKEN = "573512:AAx3RDdmFKYTKUAdHs6pvquGLUoQ4yaHBbu"
CRYPTO_BOT_API = "https://pay.crypt.bot/api"

UPLOAD_DIR = "uploads"
