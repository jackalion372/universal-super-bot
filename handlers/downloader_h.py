import os
import re
import html
import asyncio
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction, ChatType
from aiogram.types import Message, CallbackQuery, FSInputFile, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from modules.downloader.fast_downloader import fast_download_media, detect_platform
from core.database import log_stat

router = Router()

URL_REGEX = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)")

async def keep_action(bot: Bot, chat_id: int, action: ChatAction, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception:
            pass
        await asyncio.sleep(2)

@router.message(F.text.regexp(URL_REGEX))
async def handle_url_message(message: Message, bot: Bot):
    # Guruhlarda va shaxsiy chatlarda avtomatik tutib olish
    url_match = URL_REGEX.search(message.text)
    if not url_match:
        return
        
    url = url_match.group(0)
    platform = detect_platform(url)
    
    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.RECORD_VIDEO, stop_event))
    
    # Status xabari
    status_msg = await message.answer(f"⚡️ <b>{platform.capitalize()}</b> havolasi uzatilmoqda...", parse_mode="HTML")
    
    try:
        result = await fast_download_media(url, extract_audio=False)
    finally:
        stop_event.set()
        await action_task
        
    if not result.get("success"):
        await status_msg.edit_text(f"❌ <b>Kechirasiz, media yuklab olinmadi.</b>\n\n{html.escape(result.get('error', 'Noma''lum xatolik'))}", parse_mode="HTML")
        return

    # 1. Katta (2 soatlik) videolar uchun to'g'ridan-to'g'ri HD havola
    if result.get("is_large"):
        safe_title = html.escape(result.get("title", "Video"))
        direct_url = result.get("direct_url", url)
        
        caption_text = (
            f"🎬 <b>{safe_title}</b>\n\n"
            f"⚠️ <b>Ushbu video hajmi va davomiyligi juda katta (2 soat+).</b>\n"
            f"Telegram cheklovi (50MB) tufayli quyidagi tugmani bosib <b>HD formatda</b> to'g'ridan-to'g'ri yuklab olishingiz mumkin:"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 HD Videoni Yuklab Olish", url=direct_url)]
        ])
        
        await message.answer(caption_text, parse_mode="HTML", reply_markup=kb)
        log_stat(message.from_user.id, "download_large", platform)
        await status_msg.delete()
        return

    raw_title = result.get("title", "Media")
    safe_title = html.escape(raw_title)
    caption = f"🎬 <b>{safe_title}</b>\n\n🤖 @Mr_nafi_bot orqali yuklandi"
    
    is_audio = result.get("is_audio", False)
    is_image = result.get("is_image", False)
    direct_url = result.get("direct_url")
    file_path = result.get("file_path")

    upload_stop = asyncio.Event()
    up_action = ChatAction.UPLOAD_AUDIO if is_audio else (ChatAction.UPLOAD_PHOTO if is_image else ChatAction.UPLOAD_VIDEO)
    up_task = asyncio.create_task(keep_action(bot, message.chat.id, up_action, upload_stop))

    try:
        # 🚀 Direct Stream Mode (1-2 soniyalik ultra-tezlikda yuborish)
        if direct_url:
            media_input = URLInputFile(direct_url)
            if is_audio:
                await message.answer_audio(audio=media_input, caption=caption, parse_mode="HTML")
            elif is_image:
                await message.answer_photo(photo=media_input, caption=caption, parse_mode="HTML")
            else:
                await message.answer_video(video=media_input, caption=caption, parse_mode="HTML")
            await status_msg.delete()
            log_stat(message.from_user.id, "download_fast", platform)
            return

        # Zaxira fayl rejimi
        if file_path and os.path.exists(file_path):
            media_file = FSInputFile(file_path)
            if is_audio:
                await message.answer_audio(audio=media_file, caption=caption, parse_mode="HTML")
            elif is_image:
                await message.answer_photo(photo=media_file, caption=caption, parse_mode="HTML")
            else:
                await message.answer_video(video=media_file, caption=caption, parse_mode="HTML")
            await status_msg.delete()
            log_stat(message.from_user.id, "download_fallback", platform)
    except Exception as e:
        # Garovli zaxira: Direct Stream rad etilsa, mahalliy fayldan uzatish
        if file_path and os.path.exists(file_path):
            try:
                doc_file = FSInputFile(file_path)
                await message.answer_document(document=doc_file, caption=f"📄 {safe_title}\n\n🤖 @Mr_nafi_bot", parse_mode="HTML")
                await status_msg.delete()
            except Exception:
                await status_msg.edit_text(f"❌ Faylni yuborishda xatolik: {html.escape(str(e))}", parse_mode="HTML")
        else:
            await status_msg.edit_text(f"❌ Faylni uzatishda xatolik yuz berdi.", parse_mode="HTML")
    finally:
        upload_stop.set()
        await up_task
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
