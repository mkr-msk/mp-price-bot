import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from dotenv import load_dotenv
from gsheets import get_articles_text, add_article, remove_article
from wb_parser import fetch_price
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ───── Загрузка переменных ─────
load_dotenv()
MODE = os.getenv("MODE", "local")
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("DOMAIN", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/tg/")
PORT = int(os.getenv("PORT", 8080))
TZ = os.getenv("TZ", "Europe/Moscow")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# ───── Базовая настройка ─────
logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ───── Планировщик ─────
async def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(fetch_price, "cron", hour=10, minute=0)
    scheduler.start()
    logging.info("🕒 Планировщик запущен")

# ───── Команды ─────
@dp.message(F.text == "/start")
async def cmd_start(msg: types.Message):
    if msg.from_user.id in ADMIN_IDS:
        await msg.answer("✅ Бот готов к работе. Введите /help для списка команд.")
    else:
        await msg.answer("⛔ Доступ запрещён.")

@dp.message(F.text == "/help")
async def cmd_help(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ Нет доступа.")
        return
    await msg.answer("""
📋 Команды:
/add <артикул> — добавить
/del <артикул> — удалить
/list — список артикулов
/check — парсить вручную
/help — справка
""")

@dp.message(F.text == "/list")
async def cmd_list(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer(get_articles_text())

@dp.message(F.text.startswith("/add "))
async def cmd_add(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("⚠️ Использование: /add <артикул>")
        return
    added = add_article(parts[1])
    await msg.answer("✅ Добавлен." if added else "ℹ️ Уже есть.")

@dp.message(F.text.startswith("/del "))
async def cmd_del(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    parts = msg.text.strip().split()
    if len(parts) != 2:
        await msg.answer("⚠️ Использование: /del <артикул>")
        return
    removed = remove_article(parts[1])
    await msg.answer("🗑 Удалён." if removed else "⚠️ Не найден.")

@dp.message(F.text == "/check")
async def cmd_check(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer("⏳ Парсинг запущен...")
    await fetch_price()
    await msg.answer("✅ Завершено.")

# ───── Webhook режим ─────
async def on_startup(app: web.Application):
    if USE_WEBHOOK:
        url = DOMAIN.rstrip("/") + WEBHOOK_PATH
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(url)
        logging.info(f"✅ Webhook установлен: {url}")
    await setup_scheduler()

def create_webhook_app() -> web.Application:
    app = web.Application()
    app.on_startup.append(on_startup)
    SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)
    return app

# ───── Polling режим ─────
async def start_polling():
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_scheduler()
    await dp.start_polling(bot)

# ───── Точка входа ─────
def main():
    if USE_WEBHOOK:
        logging.info("🚀 Запуск в режиме WEBHOOK")
        app = create_webhook_app()
        web.run_app(app, host="0.0.0.0", port=PORT)
    else:
        logging.info("🧪 Запуск в режиме POLLING")
        asyncio.run(start_polling())

if __name__ == "__main__":
    main()
