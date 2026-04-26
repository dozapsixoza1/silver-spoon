from fastapi import FastAPI, Request, BackgroundTasks
import asyncpg
from config import POSTGRES_DSN, CRYPTO_BOT_TOKEN
import hashlib
import hmac

app = FastAPI()

async def add_credits(user_id: int, credits: int):
    conn = await asyncpg.connect(POSTGRES_DSN)
    await conn.execute("UPDATE users SET credits = credits + $1 WHERE tg_id = $2", credits, user_id)
    await conn.close()

def verify_webhook(data: bytes, signature: str) -> bool:
    secret = hashlib.sha256(CRYPTO_BOT_TOKEN.encode()).digest()
    computed = hmac.new(secret, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)

@app.post("/crypto_webhook")
async def crypto_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("Crypto-Pay-API-Signature")
    if not verify_webhook(body, signature):
        return {"ok": False}
    update = await request.json()
    if update["update_type"] == "invoice_paid":
        payload = update["payload"]
        url = payload.get("paid_btn_url", "")
        if "start=pay_" in url:
            parts = url.split("pay_")[1].split("_")
            user_id = int(parts[0])
            credits = int(parts[1])
            background_tasks.add_task(add_credits, user_id, credits)
    return {"ok": True}
