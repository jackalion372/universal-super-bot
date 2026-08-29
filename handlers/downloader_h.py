import os
import re
import html
import hashlib
import asyncio
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction, ChatType
from aiogram.types import (
    Message, CallbackQuery, FSInputFile, URLInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo
)
from modules.downloader.fast_downloader import fast_download_media, detect_platform
from core.database import log_stat, get_cached_file, save_cached_file

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
    url_match = URL_REGEX.search(message.text)
    if not url_match:
        return
        
    url = url_match.group(0)
    platform = detect_platform(url)
    url_hash = hashlib.md5(url.encode()).hexdigest()

    # 🚀 0.01 SONIYALIK TELEGRAM FILE_ID KESH (Instant Telegram Caching)
    cached = get_cached_file(url_hash)
    if cached:
        cached_file_id = cached["file_id"]
        cached_type = cached["file_type"]
        caption = cached["caption"] or f"🎬 🤖 @Mr_nafi_bot orqali yuklandi"
        try:
            if cached_type == "video":
                await message.answer_video(video=cached_file_id, caption=caption, parse_mode="HTML")
            elif cached_type == "audio":
                await message.answer_audio(audio=cached_file_id, caption=caption, parse_mode="HTML")
            elif cached_type == "photo":
                await message.answer_photo(photo=cached_file_id, caption=caption, parse_mode="HTML")
            log_stat(message.from_user.id, "download_cache", platform)
            return
        except Exception:
            pass

    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.RECORD_VIDEO, stop_event))
    status_msg = await message.answer(f"⚡️ <b>{platform.capitalize()}</b> havolasi uzatilmoqda...", parse_mode="HTML")
    
    try:
        result = await fast_download_media(url, extract_audio=False)
    finally:
        stop_event.set()
        await action_task
        
    if not result.get("success"):
        err_msg = result.get("error", "Noma'lum xatolik")
        await status_msg.edit_text(f"❌ <b>Kechirasiz, media yuklab olinmadi.</b>\n\n{html.escape(err_msg)}", parse_mode="HTML")
        return


    # 1. Instagram Karusel & TikTok Foto Slaydlar (BARCHA RASMLARNI 10 TADAN ALBOM QILIB YUBORISH)
    if result.get("is_album") and result.get("media_list"):
        media_list = result["media_list"]
        safe_title = html.escape(result.get("title", "Album"))
        
        media_group = []
        for idx, item in enumerate(media_list):
            m_url = item.get("url")
            m_type = item.get("type", "photo")
            cap = f"🎬 <b>{safe_title}</b>\n\n🤖 @Mr_nafi_bot orqali yuklandi" if idx == 0 else ""
            if m_type == "video":
                media_group.append(InputMediaVideo(media=URLInputFile(m_url), caption=cap, parse_mode="HTML"))
            else:
                media_group.append(InputMediaPhoto(media=URLInputFile(m_url), caption=cap, parse_mode="HTML"))
                
        if media_group:
            try:
                # 10 tadan bo'lib yuborish (Telegram 10 ta media guruhi limiti)
                for i in range(0, len(media_group), 10):
                    chunk = media_group[i:i+10]
                    await message.answer_media_group(media=chunk)
                await status_msg.delete()
                log_stat(message.from_user.id, "download_album", platform)
                return
            except Exception as e_album:
                logger.warning(f"MediaGroup error: {e_album}")

    # 2. Katta (2 soatlik) videolar uchun HD havola
    if result.get("is_large"):
        safe_title = html.escape(result.get("title", "Video"))
        direct_url = result.get("direct_url", url)
        caption_text = (
            f"🎬 <b>{safe_title}</b>\n\n"
            f"⚠️ <b>Ushbu video hajmi va davomiyligi juda katta (2 soat+).</b>\n"
            f"Telegram cheklovi (50MB) tufayli quyidagi tugmani bosib <b>HD formatda</b> to'g'ridan-to'g'ri yuklab olishingiz mumkin:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📥 HD Videoni Yuklab Olish", url=direct_url)]])
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
        sent_msg = None
        if direct_url:
            media_input = URLInputFile(direct_url)
            if is_audio:
                sent_msg = await message.answer_audio(audio=media_input, caption=caption, parse_mode="HTML")
                save_cached_file(url_hash, sent_msg.audio.file_id, "audio", caption)
            elif is_image:
                sent_msg = await message.answer_photo(photo=media_input, caption=caption, parse_mode="HTML")
                save_cached_file(url_hash, sent_msg.photo[-1].file_id, "photo", caption)
            else:
                sent_msg = await message.answer_video(video=media_input, caption=caption, parse_mode="HTML")
                save_cached_file(url_hash, sent_msg.video.file_id, "video", caption)
            await status_msg.delete()
            log_stat(message.from_user.id, "download_fast", platform)
            return

        if file_path and os.path.exists(file_path):
            media_file = FSInputFile(file_path)
            if is_audio:
                sent_msg = await message.answer_audio(audio=media_file, caption=caption, parse_mode="HTML")
                save_cached_file(url_hash, sent_msg.audio.file_id, "audio", caption)
            elif is_image:
                sent_msg = await message.answer_photo(photo=media_file, caption=caption, parse_mode="HTML")
                save_cached_file(url_hash, sent_msg.photo[-1].file_id, "photo", caption)
            else:
                sent_msg = await message.answer_video(video=media_file, caption=caption, parse_mode="HTML")
                save_cached_file(url_hash, sent_msg.video.file_id, "video", caption)
            await status_msg.delete()
            log_stat(message.from_user.id, "download_fallback", platform)
    except Exception as e:
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
