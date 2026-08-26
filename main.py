import asyncio
import os
import time
import requests
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from core.config import BOT_TOKEN, DOWNLOADS_DIR, TEMP_DIR, logger
from core.database import init_db
from handlers import start, admin_h, downloader_h, shazam_h, ai_h, tools_h

# Render Free Web Service Health Check Handler
async def handle_health_check(request):
    return web.Response(text="Universal Super Bot is Running Live 24/7!")

async def start_health_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Render Health Server {port}-portda ishga tushdi.")

async def keep_alive_self_ping():
    """Render Free serverini uyquga ketishdan asrash uchun har 5 daqiqada ping"""
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://universal-super-bot.onrender.com")
    while True:
        await asyncio.sleep(300) # 5 daqiqa
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, requests.get, render_url)
            logger.info("Render Keep-Alive ping yuborildi (24/7 Faol).")
        except Exception:
            pass

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Sahifani yangilash / Boshlash"),
        BotCommand(command="menu", description="🏠 Asosiy menyuni ochish"),
        BotCommand(command="downloader", description="📥 Media yuklash (Instagram, TikTok, YT)"),
        BotCommand(command="shazam", description="🎵 Shazam & Musiqa qidiruv"),
        BotCommand(command="ai", description="🧠 Gemini AI bilan suhbat"),
        BotCommand(command="reset", description="🔄 AI suhbat xotirasini tozalash"),
        BotCommand(command="tools", description="🎨 Rasm va media vositalari"),
        BotCommand(command="contact", description="📩 Adminga to'g'ridan-to'g'ri murojaat"),
        BotCommand(command="help", description="💡 Yordam va barcha buyruqlar"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Bot buyruqlari menyusi o'rnatildi.")
    except Exception as e:
        logger.error(f"Set commands error: {e}")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(1800)
        try:
            now = time.time()
            for folder in [DOWNLOADS_DIR, TEMP_DIR]:
                for file_path in folder.glob("*"):
                    if file_path.is_file():
                        if now - os.path.getmtime(file_path) > 1800:
                            try:
                                os.remove(file_path)
                            except OSError:
                                pass
            logger.info("Vaqtinchalik fayllar tozalandi.")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN kiritilmagan! Iltimos, .env faylini to'ldiring.")
        return

    init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    await start_health_server()
    asyncio.create_task(keep_alive_self_ping())

    session = AiohttpSession()
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    await setup_bot_commands(bot)

    dp.include_router(admin_h.router)
    dp.include_router(start.router)
    dp.include_router(tools_h.router)
    dp.include_router(downloader_h.router)
    dp.include_router(shazam_h.router)
    dp.include_router(ai_h.router)

    asyncio.create_task(periodic_cleanup())

    logger.info("🚀 Universal Super Bot ishga tushdi (Anti-Sleep Keep-Alive)!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, polling_timeout=20)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
