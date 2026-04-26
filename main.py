import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import BOT_TOKEN, ADMIN_IDS, REQUIRED_CHANNELS, PRICES, UPLOAD_DIR
from database import init_db, get_user, create_user, deduct_credits, add_history, get_history
from elastic import search_es, create_index
from crypto_payments import create_invoice
from admin import admin_router
from uploader import save_upload, extract_archive, index_extracted_files

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(admin_router)

# Проверку подписки не делаем – просто показываем кнопки
async def is_subscribed(user_id: int) -> bool:
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

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    await create_user(user_id)
    text = "🔐 **FL | Osint**\nБот для пробива по базам.\n\n🔻 **Подпишитесь на каналы чтобы продолжить:**"
    await message.answer(text, reply_markup=subscription_keyboard(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    await callback.message.edit_text("✅ Доступ открыт! Используй меню.", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "search_menu")
async def search_prompt(callback: CallbackQuery):
    await callback.message.edit_text("Введите данные для поиска (телефон, ник, ФИО):", reply_markup=main_menu())

@dp.message(F.text)
async def handle_search(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user or user["credits"] < 1:
        await message.answer("❌ Нет кредитов. Купи через /start → Купить запросы")
        return
    query = message.text.strip()
    await deduct_credits(user_id)
    results = await search_es(query)
    if not results:
        await message.answer(f"По запросу «{query}» ничего не найдено. Списан 1 кредит.")
        await add_history(user_id, query, "не найдено")
        return
    text = f"🔍 Найдено {len(results)}:\n\n"
    for i, res in enumerate(results[:5], 1):
        lines = [f"{k}: {v}" for k, v in res.items() if v]
        text += f"{i}. " + "\n   ".join(lines) + "\n---\n"
    if len(text) > 4000:
        for part in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            await message.answer(part)
    else:
        await message.answer(text)
    await add_history(user_id, query, text[:500])

@dp.callback_query(lambda c: c.data == "profile")
async def profile_callback(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    text = f"👤 Профиль\nКредитов: {user['credits']}\nВсего запросов: {user['total_queries']}"
    await callback.message.edit_text(text, reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "history")
async def history_callback(callback: CallbackQuery):
    rows = await get_history(callback.from_user.id, 10)
    if not rows:
        text = "История пуста"
    else:
        text = "📜 Последние 10:\n" + "\n".join(f"🔹 {r['query']} – {r['created_at'].strftime('%d.%m %H:%M')}" for r in rows)
    await callback.message.edit_text(text, reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "buy")
async def buy_callback(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for price, credits in PRICES.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{credits} запросов – ${price}", callback_data=f"pay_{price}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    await callback.message.edit_text("💎 Выбери тариф:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def payment_callback(callback: CallbackQuery):
    price = float(callback.data.split("_")[1])
    credits = PRICES[price]
    try:
        link = await create_invoice(price, callback.from_user.id, credits)
        await callback.message.edit_text(
            f"💳 Оплати {price}$ USDT → [Ссылка]({link})\nПосле оплаты кредиты начислятся автоматически.",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "help")
async def help_callback(callback: CallbackQuery):
    text = "❓ **Помощь**\n/search <текст> — поиск\n/profile — баланс\n/buy — купить запросы\n/history — история\nПри оплате кредиты приходят автоматически."
    await callback.message.edit_text(text, reply_markup=main_menu(), parse_mode="Markdown")

# Админ: загрузка файлов (только для ADMIN_IDS)
@dp.message(F.document)
async def handle_file_upload(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Только админ.")
        return
    doc = message.document
    if doc.file_size > 2 * 1024 * 1024 * 1024:
        await message.answer("Файл >2 ГБ")
        return
    file_path = await save_upload(await bot.get_file(doc.file_id), doc.file_name)
    await message.answer(f"Файл сохранён. Распаковка и индексация...")
    extracted = await extract_archive(file_path)
    if extracted:
        total = await index_extracted_files(extracted, bot, message.chat.id)
        await message.answer(f"✅ Готово. Записей: {total}")
    else:
        await message.answer("Не удалось распаковать.")

async def on_startup():
    await init_db()
    await create_index()
    print("Бот запущен")

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
