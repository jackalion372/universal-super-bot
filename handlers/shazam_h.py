import os
import uuid
import asyncio
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, FSInputFile
from modules.shazam.shazam_service import recognize_song_from_file, search_and_download_music
from core.config import TEMP_DIR
from core.database import get_user_mode, log_stat

router = Router()

async def keep_action(bot: Bot, chat_id: int, action: ChatAction, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception:
            pass
        await asyncio.sleep(4)

@router.message(F.voice | F.video_note | F.audio | F.video)
async def handle_shazam_media(message: Message, bot: Bot):
    if get_user_mode(message.from_user.id).startswith("mode_"):
        return
        
    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.TYPING, stop_event))
    status_msg = await message.answer("🎵 **Musiqa tahlil qilinmoqda (Shazam)...**", parse_mode="Markdown")
    
    file_id = None
    if message.voice:
        file_id = message.voice.file_id
        ext = ".ogg"
    elif message.video_note:
        file_id = message.video_note.file_id
        ext = ".mp4"
    elif message.audio:
        file_id = message.audio.file_id
        ext = ".mp3"
    elif message.video:
        file_id = message.video.file_id
        ext = ".mp4"
        
    temp_file_path = str(TEMP_DIR / f"shazam_{uuid.uuid4().hex[:8]}{ext}")
    
    try:
        tg_file = await bot.get_file(file_id)
        await bot.download_file(tg_file.file_path, temp_file_path)
        
        rec_res = await recognize_song_from_file(temp_file_path)
        if not rec_res.get("success"):
            await status_msg.edit_text("🔍 **Qo'shiq aniqlanmadi.** Iltimos, musiqaning tiniqroq qismini yuboring.")
            return
            
        title = rec_res["title"]
        artist = rec_res["artist"]
        query = rec_res["query"]
        lyrics = rec_res.get("lyrics")
        
        caption = f"🎶 **Topilgan Qo'shiq:**\n\n📌 **Nomi:** {title}\n👤 **Ijrochi:** {artist}\n\n🚀 *Musiqa yuklanmoqda...*"
        await status_msg.edit_text(caption, parse_mode="Markdown")
        
        music_res = await search_and_download_music(query)
        if music_res.get("success"):
            mp3_path = music_res["file_path"]
            mp3_file = FSInputFile(mp3_path)
            track_caption = f"🎵 **{artist} - {title}**\n\n🤖 @Mr_nafi_bot orqali topildi"
            await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_AUDIO)
            await message.answer_audio(audio=mp3_file, caption=track_caption, performer=artist, title=title, parse_mode="Markdown")
            
            if lyrics:
                short_lyrics = lyrics[:1000]
                await message.answer(f"📝 **Qo'shiq matni:**\n\n{short_lyrics}")
                
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
                
            await status_msg.delete()
            log_stat(message.from_user.id, "shazam_recognize", query)
        else:
            await status_msg.edit_text(f"🎶 **Topildi:** {artist} - {title}\n(Ammo MP3 fayli yuklanmadi)")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        stop_event.set()
        await action_task
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.message(F.text, lambda msg: get_user_mode(msg.from_user.id) == "shazam" or msg.text.startswith("/shazam"))
async def handle_shazam_text_search(message: Message, bot: Bot):
    query = message.text.replace("/shazam", "").strip()
    if not query:
        await message.answer("✍️ **Musiqa qidirish uchun qo'shiq nomi, ijrochi yoki qo'shiq matnini yuboring!**", parse_mode="Markdown")
        return
        
    status_msg = await message.answer(f"🔍 **'{query}' bo'yicha musiqa qidirilmoqda...**", parse_mode="Markdown")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    res = await search_and_download_music(query)
    if res.get("success"):
        mp3_path = res["file_path"]
        title = res.get("title", query)
        artist = res.get("artist", "Artist")
        
        mp3_file = FSInputFile(mp3_path)
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_AUDIO)
        await message.answer_audio(audio=mp3_file, caption=f"🎵 **{title}**\n\n🤖 @Mr_nafi_bot orqali topildi", performer=artist, title=title)
        await status_msg.delete()
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        log_stat(message.from_user.id, "music_search", query)
    else:
        await status_msg.edit_text("❌ Hech qanday musiqa topilmadi.")

