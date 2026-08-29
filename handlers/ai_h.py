import os
import asyncio
import uuid
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message
from modules.ai.ai_engine import (
    ask_gemini_chat,
    analyze_image_with_ai,
    process_voice_with_ai,
    analyze_document_with_ai,
    clear_ai_history
)
from core.config import TEMP_DIR
from core.database import get_user_mode, log_stat

router = Router()

async def send_safe_message(message: Message, text: str):
    try:
        await message.answer(text, parse_mode="Markdown")
    except Exception:
        await message.answer(text, parse_mode=None)

async def typing_loop(bot: Bot, chat_id: int, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass

@router.message(Command("reset"))
async def cmd_reset_ai(message: Message):
    clear_ai_history(message.from_user.id)
    await message.answer("🔄 **AI suhbat xotirasi tozalandi.** Yangi suhbatni toza boshlashingiz mumkin!")

@router.message(F.text)
async def handle_ai_text_chat(message: Message, bot: Bot):
    user_id = message.from_user.id
    if get_user_mode(user_id) != "ai":
        return
        
    prompt = message.text.strip()
    
    if prompt.lower() in ["/reset", "tozalash", "xotirani tozalash"]:
        clear_ai_history(user_id)
        await message.answer("🔄 **AI xotirasi tozalandi!**")
        return
        
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(bot, message.chat.id, stop_event))
    
    try:
        response = await ask_gemini_chat(user_id, prompt)
    finally:
        stop_event.set()
        await typing_task
        
    if len(response) > 4000:
        chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for chunk in chunks:
            await send_safe_message(message, chunk)
    else:
        await send_safe_message(message, response)
        
    log_stat(user_id, "ai_chat", prompt[:30])

@router.message(F.photo)
async def handle_ai_photo(message: Message, bot: Bot):
    user_id = message.from_user.id
    if get_user_mode(user_id) != "ai":
        return
        
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(bot, message.chat.id, stop_event))
    
    photo = message.photo[-1]
    temp_path = str(TEMP_DIR / f"ai_img_{uuid.uuid4().hex[:8]}.jpg")
    
    try:
        tg_file = await bot.get_file(photo.file_id)
        await bot.download_file(tg_file.file_path, temp_path)
        
        prompt = message.caption or ""
        response = await analyze_image_with_ai(user_id, temp_path, prompt)
        
        if len(response) > 4000:
            for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
                await send_safe_message(message, chunk)
        else:
            await send_safe_message(message, response)
            
        log_stat(user_id, "ai_vision")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    finally:
        stop_event.set()
        await typing_task
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.message(F.document)
async def handle_ai_document(message: Message, bot: Bot):
    user_id = message.from_user.id
    if get_user_mode(user_id) != "ai":
        return
        
    doc = message.document
    ext = Path(doc.file_name).suffix.lower()
    
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(bot, message.chat.id, stop_event))
    
    temp_path = str(TEMP_DIR / f"ai_doc_{uuid.uuid4().hex[:8]}{ext}")
    try:
        tg_file = await bot.get_file(doc.file_id)
        await bot.download_file(tg_file.file_path, temp_path)
        
        user_prompt = message.caption or ""
        response = await analyze_document_with_ai(user_id, temp_path, user_prompt)
        
        if len(response) > 4000:
            for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
                await send_safe_message(message, chunk)
        else:
            await send_safe_message(message, response)
            
        log_stat(user_id, "ai_doc", doc.file_name)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    finally:
        stop_event.set()
        await typing_task
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.message(F.voice)
async def handle_ai_voice(message: Message, bot: Bot):
    user_id = message.from_user.id
    if get_user_mode(user_id) != "ai":
        return
        
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(bot, message.chat.id, stop_event))
    
    temp_path = str(TEMP_DIR / f"ai_voice_{uuid.uuid4().hex[:8]}.ogg")
    try:
        tg_file = await bot.get_file(message.voice.file_id)
        await bot.download_file(tg_file.file_path, temp_path)
        
        response = await process_voice_with_ai(user_id, temp_path)
        await send_safe_message(message, response)
        log_stat(user_id, "ai_voice")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    finally:
        stop_event.set()
        await typing_task
        if os.path.exists(temp_path):
            os.remove(temp_path)

