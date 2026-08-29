import os
import uuid
import asyncio
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, FSInputFile
from core.config import TEMP_DIR
from core.database import set_user_mode, get_user_mode, log_stat
from modules.media_tools.media_service import remove_background, compress_image, compress_video, extract_text_from_image, video_to_mp3
from modules.converters.converter_service import images_to_pdf, image_to_single_pdf, create_zip_archive, extract_zip_archive
from modules.text_tools.text_service import latin_to_cyrillic, cyrillic_to_latin, text_to_speech, smart_translate, check_grammar
from modules.utility_tools.utility_service import generate_qr_code, read_qr_code, get_cbu_currency_rates
from modules.tools.video_note_service import convert_video_to_round_note_with_progress

from keyboards.main_kb import get_cancel_keyboard, get_main_menu_keyboard
from keyboards.inline_kb import get_translator_lang_keyboard, get_pdf_type_keyboard

router = Router()

USER_DATA_STORE = {}

async def keep_action(bot: Bot, chat_id: int, action: ChatAction, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception:
            pass
        await asyncio.sleep(4)

# ==================== CALLBACK HANDLERS ====================

@router.callback_query(F.data.startswith("tool_"))
async def handle_tool_callback(callback: CallbackQuery):
    action = callback.data.replace("tool_", "")
    user_id = callback.from_user.id
    
    if action == "trans":
        await callback.answer()
        await callback.message.answer("🌐 **Qaysi tilga tarjima qilmoqchisiz?**\nKerakli tilni tanlang:", reply_markup=get_translator_lang_keyboard())
        return

    if action == "img2pdf":
        await callback.answer()
        await callback.message.answer("📄 **PDF turini tanlang:**", reply_markup=get_pdf_type_keyboard())
        return

    if action == "currency":
        await callback.answer("Valyuta kurslari yuklanmoqda...")
        data = await get_cbu_currency_rates()
        if data.get("success"):
            rates = data["rates"]
            txt = "💱 **O'zbekiston Markaziy Banki Rasmiy Kurslari:**\n\n"
            for ccy, info in rates.items():
                diff_sign = "+" if float(info['diff']) >= 0 else ""
                txt += f"• **1 {ccy}** = `{info['rate']}` so'm ({diff_sign}{info['diff']})\n"
            txt += f"\n📅 *Sana: {list(rates.values())[0]['date']}*"
            await callback.message.answer(txt, parse_mode="Markdown")
        else:
            await callback.message.answer("❌ Valyuta kurslarini olib bo'lmadi.")
        return

    modes_info = {
        "rembg": ("mode_rembg", "✂️ **Fonni o'chirish rejimi.**\n\nIltimos, fonini olib tashlamoqchi bo'lgan rasmni yuboring:"),
        "ocr": ("mode_ocr", "📝 **OCR (Matn ajratish) rejimi.**\n\nKitob, daftar yoki yozuvli rasm yuboring:"),
        "compress": ("mode_compress", "📦 **Siqish (Compress) rejimi.**\n\nHajmini sifatini saqlab kichraytirmoqchi bo'lgan **rasm yoki video**ni yuboring:"),
        "vid2note": ("mode_vid2note", "🎥 ➡️ ⭕️ **Videoni Dumaloq Video Note qilish rejimi.**\n\nDumaloq video (Video Message) qilmoqchi bo'lgan videongizni yuboring:"),
        "vid2mp3": ("mode_vid2mp3", "🎥 **Video -> MP3 rejimi.**\n\nAudiosini ajratib olmoqchi bo'lgan videoni yuboring:"),

        "zip": ("mode_zip", "📦 **ZIP Arxiv rejimi.**\n\nArxivlamoqchi bo'lgan fayl/rasmni yoki ochmoqchi bo'lgan `.zip` faylni yuboring:"),
        "lat2cyr": ("mode_lat2cyr", "🔤 **Lotin ➡️ Kirill rejimi.**\n\nLotin alifbosidagi matnni yuboring:"),
        "cyr2lat": ("mode_cyr2lat", "🔤 **Kirill ➡️ Lotin rejimi.**\n\nKirill alifbosidagi matnni yuboring:"),
        "tts": ("mode_tts", "🗣 **Matndan Tabiiy Ovoz (TTS) rejimi.**\n\nOvozga aylantirmoqchi bo'lgan matningizni yuboring (O'zbekcha, Ruscha yoki Inglizcha):"),
        "gram": ("mode_gram", "🖋 **Imlo tekshirish rejimi.**\n\nTekshirmoqchi bo'lgan matningizni yuboring:"),
        "genqr": ("mode_genqr", "📱 **QR Kod yaratish rejimi.**\n\nQR kod qilmoqchi bo'lgan matn yoki havolani yuboring:"),
        "readqr": ("mode_readqr", "🔍 **QR Kod o'qish rejimi.**\n\nQR kodli rasmni yuboring:")
    }
    
    if action in modes_info:
        mode_name, msg_text = modes_info[action]
        set_user_mode(user_id, mode_name)
        await callback.answer()
        await callback.message.answer(msg_text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())

@router.callback_query(F.data.startswith("trans_"))
async def handle_trans_lang(callback: CallbackQuery):
    lang_code = callback.data.replace("trans_", "")
    lang_names = {
        "uz": "O'zbek", "ru": "Rus", "en": "Ingliz", "tr": "Turk", "ar": "Arab"
    }
    target_name = lang_names.get(lang_code, "O'zbek")
    user_id = callback.from_user.id
    set_user_mode(user_id, f"mode_trans_{lang_code}")
    await callback.answer()
    await callback.message.answer(f"🌐 **{target_name} tiliga tarjima rejimi tanlandi.**\n\nTarjima qilmoqchi bo'lgan matningizni yuboring:", reply_markup=get_cancel_keyboard())

@router.callback_query(F.data.startswith("pdf_"))
async def handle_pdf_choice(callback: CallbackQuery):
    pdf_type = callback.data.replace("pdf_", "")
    user_id = callback.from_user.id
    if pdf_type == "combined":
        set_user_mode(user_id, "mode_pdf_combined")
        USER_DATA_STORE[user_id] = []
        await callback.answer()
        await callback.message.answer("📑 **Bitta jamlangan PDF rejimi.**\nRasmlarni birma-bir yuboring. Tugagach **/done** yoki 'Tayyor' deb yozing:", reply_markup=get_cancel_keyboard())
    else:
        set_user_mode(user_id, "mode_pdf_single")
        await callback.answer()
        await callback.message.answer("📄 **Alohida PDF rejimi.**\nRasmni yuboring, uni darhol alohida PDF qilib beraman:", reply_markup=get_cancel_keyboard())

# ==================== MEDIA INPUTS (PHOTOS & VIDEOS) ====================

@router.message(F.photo)
async def handle_tool_photos(message: Message, bot: Bot):
    user_id = message.from_user.id
    mode = get_user_mode(user_id)
    photo = message.photo[-1]
    
    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.TYPING, stop_event))
    
    temp_in = str(TEMP_DIR / f"in_{uuid.uuid4().hex[:8]}.jpg")
    try:
        tg_file = await bot.get_file(photo.file_id)
        await bot.download_file(tg_file.file_path, temp_in)
        
        if mode == "mode_rembg":
            status = await message.answer("✂️ **Fon o'chirilmoqda...**", parse_mode="Markdown")
            temp_out = str(TEMP_DIR / f"nobg_{uuid.uuid4().hex[:8]}.png")
            success = remove_background(temp_in, temp_out)
            if success and os.path.exists(temp_out):
                doc_file = FSInputFile(temp_out, filename="no_background.png")
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                await message.answer_document(document=doc_file, caption="✅ **Fon muvaffaqiyatli olib tashlandi!**")
                os.remove(temp_out)
            else:
                await message.answer("⚠️ Fonni olib tashlashda xatolik yuz berdi.")
            await status.delete()
            
        elif mode == "mode_ocr":
            status = await message.answer("📝 **Rasmdagi matn ajratilmoqda...**", parse_mode="Markdown")
            text = await extract_text_from_image(user_id, temp_in)
            await status.edit_text(f"📋 **Ajratib olingan matn:**\n\n`{text}`", parse_mode="Markdown")
            
        elif mode == "mode_compress":
            status = await message.answer("📦 **Rasm siqilmoqda...**", parse_mode="Markdown")
            temp_out = str(TEMP_DIR / f"comp_{uuid.uuid4().hex[:8]}.jpg")
            if compress_image(temp_in, temp_out):
                in_size = os.path.getsize(temp_in) // 1024
                out_size = os.path.getsize(temp_out) // 1024
                doc_file = FSInputFile(temp_out, filename="compressed.jpg")
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                await message.answer_document(document=doc_file, caption=f"✅ **Rasm siqildi:** {in_size}KB ➡️ {out_size}KB")
                os.remove(temp_out)
            await status.delete()
            
        elif mode == "mode_pdf_single":
            status = await message.answer("📄 **PDF yaratilmoqda...**", parse_mode="Markdown")
            temp_pdf = str(TEMP_DIR / f"doc_{uuid.uuid4().hex[:8]}.pdf")
            if image_to_single_pdf(temp_in, temp_pdf):
                doc_file = FSInputFile(temp_pdf, filename="document.pdf")
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                await message.answer_document(document=doc_file, caption="✅ **PDF tayyor!**")
                os.remove(temp_pdf)
            await status.delete()
            
        elif mode == "mode_pdf_combined":
            if user_id not in USER_DATA_STORE:
                USER_DATA_STORE[user_id] = []
            USER_DATA_STORE[user_id].append(temp_in)
            count = len(USER_DATA_STORE[user_id])
            await message.answer(f"✅ **{count}-rasm qabul qilindi.** Yana rasm yuboring yoki barchasini bitta PDF qilish uchun **/done** deb yozing.")
            return
            
        elif mode == "mode_readqr":
            status = await message.answer("🔍 **QR kod o'qilmoqda...**", parse_mode="Markdown")
            data = await read_qr_code(user_id, temp_in)
            await status.edit_text(f"📱 **QR Kod tarkibi:**\n\n`{data}`", parse_mode="Markdown")
            
        elif mode == "mode_zip":
            temp_zip = str(TEMP_DIR / f"archive_{uuid.uuid4().hex[:8]}.zip")
            if create_zip_archive([temp_in], temp_zip):
                doc_file = FSInputFile(temp_zip, filename="photos.zip")
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                await message.answer_document(document=doc_file, caption="✅ **ZIP arxiv tayyor!**")
                os.remove(temp_zip)
    finally:
        stop_event.set()
        await action_task
        if mode != "mode_pdf_combined" and os.path.exists(temp_in):
            os.remove(temp_in)

@router.message(F.video | F.video_note)
async def handle_tool_videos(message: Message, bot: Bot):
    user_id = message.from_user.id
    mode = get_user_mode(user_id)
    
    stop_event = asyncio.Event()
    action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.RECORD_VIDEO, stop_event))
    
    temp_vid = str(TEMP_DIR / f"vid_{uuid.uuid4().hex[:8]}.mp4")
    try:
        vid_id = message.video.file_id if message.video else message.video_note.file_id
        tg_file = await bot.get_file(vid_id)
        await bot.download_file(tg_file.file_path, temp_vid)

        
        if mode == "mode_compress":
            status = await message.answer("📦 **Video sifatini saqlab siqilmoqda...**", parse_mode="Markdown")
            temp_out = str(TEMP_DIR / f"comp_{uuid.uuid4().hex[:8]}.mp4")
            if compress_video(temp_vid, temp_out):
                in_mb = round(os.path.getsize(temp_vid) / (1024*1024), 2)
                out_mb = round(os.path.getsize(temp_out) / (1024*1024), 2)
                vid_file = FSInputFile(temp_out)
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)
                await message.answer_video(video=vid_file, caption=f"✅ **Video siqildi:** {in_mb}MB ➡️ {out_mb}MB (Sifat saqlandi)")
                os.remove(temp_out)
            await status.delete()
            
        elif mode == "mode_vid2note":
            status = await message.answer("⚡️ **Dumaloq Video Note tayyorlanmoqda... 0%** [░░░░░░░░░░]", parse_mode="Markdown")
            
            async def update_progress(pct: int):
                filled = pct // 10
                bar = "█" * filled + "░" * (10 - filled)
                try:
                    await status.edit_text(f"⚡️ **Dumaloq Video Note tayyorlanmoqda... {pct}%** [{bar}]", parse_mode="Markdown")
                except Exception:
                    pass

            vnote_path = await convert_video_to_round_note_with_progress(temp_vid, update_progress)
            
            if vnote_path and os.path.exists(vnote_path):
                try:
                    await status.edit_text("⚡️ **Dumaloq Video Note tayyorlandi! 100%** [██████████]", parse_mode="Markdown")
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
                await status.delete()
                vnote_file = FSInputFile(vnote_path)
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VIDEO_NOTE)
                await message.answer_video_note(video_note=vnote_file)
                if os.path.exists(vnote_path):
                    os.remove(vnote_path)
            else:
                await status.delete()
                await message.answer("❌ Videoni dumaloq qilishda xatolik yuz berdi. Iltimos, boshqa video bilan sinab ko'ring.")



        elif mode == "mode_vid2mp3":

            status = await message.answer("🎵 **Audio ajratib olinmoqda...**", parse_mode="Markdown")
            temp_audio = str(TEMP_DIR / f"audio_{uuid.uuid4().hex[:8]}.mp3")
            if video_to_mp3(temp_vid, temp_audio):
                audio_file = FSInputFile(temp_audio)
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_AUDIO)
                await message.answer_audio(audio=audio_file, caption="🎵 **Videodan ajratilgan MP3 audio**")
                os.remove(temp_audio)
            await status.delete()
    finally:
        stop_event.set()
        await action_task
        if os.path.exists(temp_vid):
            os.remove(temp_vid)

@router.message(F.document)
async def handle_tool_documents(message: Message, bot: Bot):
    user_id = message.from_user.id
    mode = get_user_mode(user_id)
    doc = message.document
    
    if mode == "mode_zip" and doc.file_name.lower().endswith(".zip"):
        status = await message.answer("📦 **ZIP arxiv ochilmoqda...**", parse_mode="Markdown")
        temp_zip = str(TEMP_DIR / f"in_{uuid.uuid4().hex[:8]}.zip")
        extract_dir = str(TEMP_DIR / f"ext_{uuid.uuid4().hex[:8]}")
        try:
            tg_file = await bot.get_file(doc.file_id)
            await bot.download_file(tg_file.file_path, temp_zip)
            files = extract_zip_archive(temp_zip, extract_dir)
            if files:
                await status.edit_text(f"✅ **{len(files)} ta fayl arxivdan chiqarildi:**")
                for f in files[:10]:
                    if os.path.isfile(f):
                        await message.answer_document(document=FSInputFile(f))
            else:
                await status.edit_text("⚠️ Arxiv bo'sh yoki ochib bo'lmadi.")
        finally:
            if os.path.exists(temp_zip):
                os.remove(temp_zip)

# ==================== TEXT INPUTS & COMMANDS ====================

@router.message(F.text == "/done")
@router.message(F.text.lower() == "tayyor")
async def handle_pdf_done(message: Message, bot: Bot):
    user_id = message.from_user.id
    if user_id in USER_DATA_STORE and USER_DATA_STORE[user_id]:
        status = await message.answer("📄 **Barcha rasmlar bitta PDF ga jamlanmoqda...**", parse_mode="Markdown")
        temp_pdf = str(TEMP_DIR / f"combined_{uuid.uuid4().hex[:8]}.pdf")
        img_paths = USER_DATA_STORE[user_id]
        if images_to_pdf(img_paths, temp_pdf):
            doc_file = FSInputFile(temp_pdf, filename="all_images.pdf")
            await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
            await message.answer_document(document=doc_file, caption=f"✅ **{len(img_paths)} ta rasm bitta PDF ga birlashtirildi!**")
            os.remove(temp_pdf)
        for p in img_paths:
            if os.path.exists(p):
                os.remove(p)
        USER_DATA_STORE[user_id] = []
        await status.delete()
    else:
        await message.answer("⚠️ Hali hech qanday rasm yuklanmagan.")

@router.message(F.text, lambda msg: get_user_mode(msg.from_user.id).startswith("mode_"))
async def handle_tool_text_inputs(message: Message, bot: Bot):
    user_id = message.from_user.id
    mode = get_user_mode(user_id)
    text = message.text.strip()
    
    if mode == "mode_lat2cyr":
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        converted = latin_to_cyrillic(text)
        await message.answer(f"🔤 **Kirillcha matn:**\n\n`{converted}`", parse_mode="Markdown")
        
    elif mode == "mode_cyr2lat":
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        converted = cyrillic_to_latin(text)
        await message.answer(f"🔤 **Lotincha matn:**\n\n`{converted}`", parse_mode="Markdown")
        
    elif mode == "mode_tts":
        stop_event = asyncio.Event()
        action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.RECORD_VOICE, stop_event))
        status = await message.answer("🎙 **Tabiiy audio tayyorlanmoqda (Neural HD)...**", parse_mode="Markdown")
        temp_audio = str(TEMP_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3")
        try:
            if await text_to_speech(text, temp_audio, lang="uz"):
                audio_file = FSInputFile(temp_audio)
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)
                await message.answer_voice(voice=audio_file, caption="🗣 **Matndan yaratilgan jonli audio**")
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
        finally:
            stop_event.set()
            await action_task
            await status.delete()
        
    elif mode.startswith("mode_trans"):
        lang_code = mode.replace("mode_trans_", "") if mode != "mode_trans" else "uz"
        lang_names = {"uz": "o'zbek", "ru": "rus", "en": "ingliz", "tr": "turk", "ar": "arab"}
        target_name = lang_names.get(lang_code, "o'zbek")
        
        stop_event = asyncio.Event()
        action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.TYPING, stop_event))
        status = await message.answer(f"🌐 **{target_name.capitalize()} tiliga tarjima qilinmoqda...**", parse_mode="Markdown")
        try:
            res = await smart_translate(user_id, text, target_lang=target_name)
            await status.edit_text(f"🌐 **Tarjima ({target_name}):**\n\n{res}", parse_mode="Markdown")
        finally:
            stop_event.set()
            await action_task
        
    elif mode == "mode_gram":
        stop_event = asyncio.Event()
        action_task = asyncio.create_task(keep_action(bot, message.chat.id, ChatAction.TYPING, stop_event))
        status = await message.answer("🖋 **Imlo tekshirilmoqda...**", parse_mode="Markdown")
        try:
            res = await check_grammar(user_id, text)
            await status.edit_text(f"🖋 **Tekshiruv natijasi:**\n\n{res}", parse_mode="Markdown")
        finally:
            stop_event.set()
            await action_task
        
    elif mode == "mode_genqr":
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
        status = await message.answer("📱 **QR Kod yaratilmoqda...**", parse_mode="Markdown")
        temp_qr = str(TEMP_DIR / f"qr_{uuid.uuid4().hex[:8]}.png")
        if generate_qr_code(text, temp_qr):
            photo_file = FSInputFile(temp_qr)
            await message.answer_photo(photo=photo_file, caption=f"📱 **QR Kod:**\n`{text[:50]}`", parse_mode="Markdown")
            if os.path.exists(temp_qr):
                os.remove(temp_qr)
        await status.delete()
