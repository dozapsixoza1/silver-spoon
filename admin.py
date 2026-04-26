from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_IDS
from database import get_all_users, add_credits
import asyncio

admin_router = Router()

@admin_router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Команды:\n/addcredits <user_id> <количество>\n/stats\n/broadcast <текст>")

@admin_router.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = await get_all_users()
    total_credits = sum(u['credits'] for u in users)
    await message.answer(f"Пользователей: {len(users)}\nВсего кредитов: {total_credits}")

@admin_router.message(Command("addcredits"))
async def addcredits(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /addcredits user_id количество")
        return
    _, uid, amt = parts
    await add_credits(int(uid), int(amt))
    await message.answer(f"Начислено {amt} кредитов пользователю {uid}")

@admin_router.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        return
    users = await get_all_users()
    sent = 0
    for u in users:
        try:
            await message.bot.send_message(u['tg_id'], text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"Рассылка отправлена {sent} пользователям")
