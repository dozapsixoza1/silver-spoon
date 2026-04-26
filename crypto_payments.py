import aiohttp
from config import CRYPTO_BOT_TOKEN, CRYPTO_BOT_API

async def create_invoice(amount: float, user_id: int, credits: int) -> str:
    url = f"{CRYPTO_BOT_API}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": f"{credits} запросов FL Osint",
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://t.me/FL_Osint_Bot?start=pay_{user_id}_{credits}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]["bot_invoice_url"]
            raise Exception(f"CryptoBot error: {data}")
