import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.types import BotCommand, BotCommandScopeChat
from aiohttp import web
from dotenv import load_dotenv
from wb_parser import fetch_price
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gsheets import add_article, get_articles_text, remove_article


# ───── Загрузка конфигурации ─────
load_dotenv()
MODE         = os.getenv("MODE", "local")
BOT_TOKEN    = os.getenv("BOT_TOKEN")
DOMAIN       = os.getenv("DOMAIN", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/")
PORT         = int(os.getenv("PORT", "8080"))
TZ           = os.getenv("TZ", "Europe/Moscow")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# ───── Логирование и инициализация ─────
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ───── Планировщик ─────
async def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(fetch_price, "cron", hour=10, minute=0)  # каждый день в 10:00
    scheduler.start()
    logging.info("🕒 Планировщик запущен")

# ───── Polling (локальный запуск) ─────
async def polling_main():
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_scheduler()
    logging.info("👂 Polling запущен")
    await dp.start_polling(bot)

# ───── Webhook (прод) ─────
async def on_startup(app: web.Application):
    webhook_url = DOMAIN.rstrip("/") + WEBHOOK_PATH
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    await setup_scheduler()
    logging.info(f"🔗 Webhook установлен на {webhook_url}")

def webhook_app() -> web.Application:
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    return app

# ───── Хендлеры ─────
@dp.message(F.text.startswith("/add "))
async def cmd_add(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ У тебя нет доступа к этой команде.")
        return

    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("⚠️ Использование: /add <артикул>")
        return

    articul = parts[1]
    if add_article(articul):
        await msg.answer(f"✅ Артикул {articul} добавлен в список.")
    else:
        await msg.answer(f"ℹ️ Артикул {articul} уже есть в таблице.")

@dp.message(F.text == "/list")
async def cmd_list(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ У тебя нет доступа к этой команде.")
        return
    text = get_articles_text()
    await msg.answer(text)

@dp.message(F.text.startswith("/del "))
async def cmd_del(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ У тебя нет доступа к этой команде.")
        return

    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("⚠️ Использование: /del <артикул>")
        return

    articul = parts[1]
    if remove_article(articul):
        await msg.answer(f"🗑 Артикул {articul} удалён.")
    else:
        await msg.answer(f"⚠️ Артикул {articul} не найден.")

@dp.message(F.text == "/help")
async def cmd_help(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ У тебя нет доступа к списку команд.")
        return

    help_text = """
📋 <b>Доступные команды:</b>

/add &lt;артикул&gt; — добавить товар в мониторинг
/del &lt;артикул&gt; — удалить товар из списка
/list — показать текущие артикулы
/help — показать эту справку
/check — ручной запуск парсинга (вместо ожидания по расписанию)
"""
    await msg.answer(help_text.strip(), parse_mode="HTML")

@dp.message(F.text == "/check")
async def cmd_check(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ У тебя нет доступа к этой команде.")
        return

    await msg.answer("⏳ Парсинг запущен, ждите...")
    try:
        await fetch_price()
        await msg.answer("✅ Парсинг завершён.")
    except Exception as e:
        await msg.answer(f"❌ Ошибка парсинга: {e}")

@dp.message(F.text == "/start")
async def cmd_start(msg: types.Message):
    is_admin = msg.from_user.id in ADMIN_IDS

    if is_admin:
        await bot.set_my_commands(
            commands=[
                BotCommand(command="add", description="Добавить артикул"),
                BotCommand(command="del", description="Удалить артикул"),
                BotCommand(command="list", description="Список артикулов"),
                BotCommand(command="check", description="Ручной парсинг"),
                BotCommand(command="help", description="Справка"),
            ],
            scope=BotCommandScopeChat(chat_id=msg.chat.id)
        )
        await msg.answer("👋 Привет, админ!\nМеню команд установлено. Введи /help для справки.")
    else:
        await msg.answer("👋 Привет!\nЭтот бот предназначен только для администраторов.")


# ───── Точка входа ─────
def main():
    if MODE == "prod":
        logging.info("🚀 PROD режим (Webhook)")
        web.run_app(webhook_app(), host="0.0.0.0", port=PORT)
    else:
        logging.info("🧪 LOCAL режим (Polling)")
        asyncio.run(polling_main())

if __name__ == "__main__":
    main()
