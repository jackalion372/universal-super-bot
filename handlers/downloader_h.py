import os
import re
import asyncio
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, FSInputFile
from modules.downloader.downloader import download_media, detect_platform
from core.database import log_stat

router = Router()

URL_REGEX = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)")

async def keep_action(bot: Bot, chat_id: int, action: ChatAction, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception:
            pass
        await asyncio.sleep(4)

@router.message(F.text.regexp(URL_REGEX))
async def handle_url_message(message: Message, bot: Bot):
    url = URL_REGEX.search(message.text).group(0)
    platform = detect_platform(url)
    
    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.RECORD_VIDEO, stop_event))
    
    status_msg = await message.answer(f"⏳ **{platform.capitalize()} havolasi yuklanmoqda...**", parse_mode="Markdown")
    
    try:
        result = await download_media(url, extract_audio=False)
    finally:
        stop_event.set()
        await action_task
        
    if not result.get("success"):
        await status_msg.edit_text(f"❌ **Kechirasiz, media yuklab olinmadi.**\n\nSababi: {result.get('error', 'Noma''lum xatolik')}")
        return
        
    file_path = result["file_path"]
    is_audio = result.get("is_audio", False)
    is_image = result.get("is_image", False)
    title = result.get("title", "Media")
    
    upload_stop = asyncio.Event()
    up_action = ChatAction.UPLOAD_AUDIO if is_audio else (ChatAction.UPLOAD_PHOTO if is_image else ChatAction.UPLOAD_VIDEO)
    up_task = asyncio.create_task(keep_action(bot, message.chat.id, up_action, upload_stop))
    
    try:
        media_file = FSInputFile(file_path)
        caption = f"🎬 **{title}**\n\n🤖 @Mr_nafi_bot orqali yuklandi"
        
        if is_audio:
            await message.answer_audio(audio=media_file, caption=caption, parse_mode="Markdown")
        elif is_image:
            await message.answer_photo(photo=media_file, caption=caption, parse_mode="Markdown")
        else:
            await message.answer_video(video=media_file, caption=caption, parse_mode="Markdown")
            
        log_stat(message.from_user.id, "download", platform)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Faylni yuborishda xatolik: {e}")
    finally:
        upload_stop.set()
        await up_task
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
