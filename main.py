import asyncio
import os
import time
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from core.config import BOT_TOKEN, DOWNLOADS_DIR, TEMP_DIR, logger
from core.database import init_db
from handlers import start, admin_h, downloader_h, shazam_h, ai_h, tools_h

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

    session = AiohttpSession()
    
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Buyruqlar menyusini Telegramga kiritish
    await setup_bot_commands(bot)

    # Routerni ulash
    dp.include_router(admin_h.router)
    dp.include_router(start.router)
    dp.include_router(tools_h.router)
    dp.include_router(downloader_h.router)
    dp.include_router(shazam_h.router)
    dp.include_router(ai_h.router)

    asyncio.create_task(periodic_cleanup())

    logger.info("🚀 Universal Super Bot ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, polling_timeout=20)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
