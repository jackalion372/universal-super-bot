import os
import re
import html
import asyncio
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
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
        await asyncio.sleep(3)

@router.message(F.text.regexp(URL_REGEX))
async def handle_url_message(message: Message, bot: Bot):
    url = URL_REGEX.search(message.text).group(0)
    platform = detect_platform(url)
    
    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.RECORD_VIDEO, stop_event))
    
    status_msg = await message.answer(f"⏳ <b>{platform.capitalize()}</b> havolasi yuklanmoqda...", parse_mode="HTML")
    
    try:
        result = await download_media(url, extract_audio=False)
    finally:
        stop_event.set()
        await action_task
        
    if not result.get("success"):
        await status_msg.edit_text(f"❌ <b>Kechirasiz, media yuklab olinmadi.</b>\n\nSababi: {html.escape(result.get('error', 'Noma xatolik'))}", parse_mode="HTML")
        return

    # Katta va uzun (2 soatlik) videolar uchun yuqori tezlikdagi to'g'ridan-to'g'ri havolani berish
    if result.get("is_large"):
        safe_title = html.escape(result.get("title", "Video"))
        direct_url = result.get("direct_url", url)
        
        caption_text = (
            f"🎬 <b>{safe_title}</b>\n\n"
            f"⚠️ <b>Ushbu video hajmi va davomiyligi juda katta (2 soat+).</b>\n"
            f"Telegram'ning 50MB bot cheklovi sababli, quyidagi tugmani bosib <b>HD formatda</b> to'g'ridan-to'g'ri yuklab olishingiz mumkin:"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 HD Videoni Yuklab Olish", url=direct_url)]
        ])
        
        await message.answer(caption_text, parse_mode="HTML", reply_markup=kb)
        log_stat(message.from_user.id, "download_large", platform)
        await status_msg.delete()
        return
        
    file_path = result["file_path"]
    is_audio = result.get("is_audio", False)
    is_image = result.get("is_image", False)
    raw_title = result.get("title", "Media")
    safe_title = html.escape(raw_title)
    
    upload_stop = asyncio.Event()
    up_action = ChatAction.UPLOAD_AUDIO if is_audio else (ChatAction.UPLOAD_PHOTO if is_image else ChatAction.UPLOAD_VIDEO)
    up_task = asyncio.create_task(keep_action(bot, message.chat.id, up_action, upload_stop))
    
    try:
        media_file = FSInputFile(file_path)
        caption = f"🎬 <b>{safe_title}</b>\n\n🤖 @Mr_nafi_bot orqali yuklandi"
        
        if is_audio:
            await message.answer_audio(audio=media_file, caption=caption, parse_mode="HTML")
        elif is_image:
            await message.answer_photo(photo=media_file, caption=caption, parse_mode="HTML")
        else:
            await message.answer_video(video=media_file, caption=caption, parse_mode="HTML")
            
        log_stat(message.from_user.id, "download", platform)
        await status_msg.delete()
    except Exception as e:
        try:
            doc_file = FSInputFile(file_path)
            await message.answer_document(document=doc_file, caption=f"📄 {safe_title}\n\n🤖 @Mr_nafi_bot", parse_mode="HTML")
            await status_msg.delete()
        except Exception as e2:
            await status_msg.edit_text(f"❌ Faylni yuborishda xatolik: {html.escape(str(e))}", parse_mode="HTML")
    finally:
        upload_stop.set()
        await up_task
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
