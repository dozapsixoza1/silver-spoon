import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_IDS, REQUIRED_CHANNELS, PRICES, UPLOAD_DIR
from database import (init_db, get_user, create_user, set_subscribed, add_credits,
                      deduct_credits, add_history, get_history, get_all_users, search_fts)
from crypto_payments import create_invoice
from uploader import save_upload, extract_archive, index_extracted_files

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Подписка (реальная проверка через ID каналов) ----------
async def is_subscribed(user_id: int) -> bool:
    for ch in REQUIRED_CHANNELS:
        channel_id = ch.get("id")
        if not channel_id:
            continue
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status in ("left", "kicked"):
                return False
        except:
            return False
    return True

def subscription_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for ch in REQUIRED_CHANNELS:
        kb.inline_keyboard.append([InlineKeyboardButton(text=ch["name"], url=ch["url"])])
    kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")])
    return kb

def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_menu")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="profile"), InlineKeyboardButton(text="📜 История", callback_data="history")],
        [InlineKeyboardButton(text="💎 Купить запросы", callback_data="buy")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    return kb

# ---------- Старт ----------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    create_user(user_id)
    subscribed = await is_subscribed(user_id)
    if not subscribed:
        text = "🔐 **FL | Osint**\nПодпишись на каналы чтобы продолжить:"
        await message.answer(text, reply_markup=subscription_keyboard(), parse_mode="Markdown")
    else:
        set_subscribed(user_id, True)
        await message.answer("✅ Доступ открыт", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_subscribed(user_id):
        set_subscribed(user_id, True)
        await callback.message.edit_text("✅ Доступ открыт", reply_markup=main_menu())
    else:
        await callback.answer("Ты не подписан на все каналы!", show_alert=True)

# ---------- Поиск ----------
@dp.callback_query(lambda c: c.data == "search_menu")
async def search_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text("Введи данные для поиска (телефон, ник, ФИО):", reply_markup=main_menu())

@dp.message(F.text)
async def handle_search(message: types.Message):
    user_id = message.from_user.id
    if not await is_subscribed(user_id):
        await message.answer("Сначала подпишись: /start")
        return
    user = get_user(user_id)
    if not user or user["credits"] < 1:
        await message.answer("Нет кредитов. Купи через меню.")
        return
    query = message.text.strip()
    deduct_credits(user_id)
    results = search_fts(query)
    if not results:
        await message.answer(f"По запросу '{query}' ничего не найдено. Списан 1 кредит.")
        add_history(user_id, query, "не найдено")
        return
    text = f"🔍 Найдено {len(results)}:\n\n"
    for i, res in enumerate(results[:5], 1):
        lines = [f"{k}: {v}" for k, v in res.items() if v]
        text += f"{i}. " + "\n   ".join(lines) + "\n---\n"
    for part in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(part)
    add_history(user_id, query, text[:500])

# ---------- Профиль и история ----------
@dp.callback_query(lambda c: c.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(f"👤 Кредитов: {user['credits']}\nВсего запросов: {user['total_queries']}", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "history")
async def history_callback(callback: types.CallbackQuery):
    rows = get_history(callback.from_user.id, 10)
    if not rows:
        text = "История пуста"
    else:
        text = "📜 Последние 10:\n" + "\n".join(f"🔹 {r[0]} – {r[2]}" for r in rows)
    await callback.message.edit_text(text, reply_markup=main_menu())

# ---------- Покупка ----------
@dp.callback_query(lambda c: c.data == "buy")
async def buy_callback(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for price, credits in PRICES.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{credits} запросов – ${price}", callback_data=f"pay_{price}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    await callback.message.edit_text("Выбери тариф:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def payment_callback(callback: types.CallbackQuery):
    price = float(callback.data.split("_")[1])
    credits = PRICES[price]
    try:
        link = await create_invoice(price, callback.from_user.id, credits)
        await callback.message.edit_text(f"Оплати {price}$ USDT: {link}\nПосле оплаты кредиты начислятся.", reply_markup=main_menu())
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "help")
async def help_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("Поиск по базе. /start для меню.", reply_markup=main_menu())

# ---------- Админ команды (прямо здесь) ----------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Команды админа:\n/stats\n/addcredits <user_id> <кол-во>\n/broadcast <текст>")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = get_all_users()
    total_credits = sum(u['credits'] for u in users)
    await message.answer(f"Пользователей: {len(users)}\nВсего кредитов: {total_credits}")

@dp.message(Command("addcredits"))
async def addcredits(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /addcredits user_id количество")
        return
    _, uid, amt = parts
    add_credits(int(uid), int(amt))
    await message.answer(f"Начислено {amt} кредитов пользователю {uid}")

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        return
    users = get_all_users()
    sent = 0
    for u in users:
        try:
            await bot.send_message(u['tg_id'], text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"Рассылка отправлена {sent} пользователям")

# ---------- Загрузка файлов (только админ) ----------
@dp.message(F.document)
async def handle_file_upload(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Только админ.")
        return
    doc = message.document
    if doc.file_size > 2 * 1024 * 1024 * 1024:
        await message.answer("Файл >2ГБ")
        return
    file_path = await save_upload(await bot.get_file(doc.file_id), doc.file_name)
    await message.answer("Файл сохранён. Распаковка и индексация...")
    extracted = await extract_archive(file_path)
    if extracted:
        total = await index_extracted_files(extracted, bot, message.chat.id)
        await message.answer(f"✅ Готово. Записей: {total}")
    else:
        await message.answer("Не удалось распаковать.")

# ---------- Запуск ----------
async def main():
    init_db()
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
