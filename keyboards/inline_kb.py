from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_media_tools_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✂️ Fonni o'chirish (PNG)", callback_data="tool_rembg"),
            InlineKeyboardButton(text="📝 OCR (Yozuvni matnga)", callback_data="tool_ocr")
        ],
        [
            InlineKeyboardButton(text="🎥 ➡️ ⭕️ Videoni Dumaloq qilish", callback_data="tool_vid2note"),
            InlineKeyboardButton(text="🎥 Video -> MP3", callback_data="tool_vid2mp3")
        ],
        [
            InlineKeyboardButton(text="📦 Rasm / Video Siqish", callback_data="tool_compress")
        ]
    ])


def get_file_tools_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖼 ➡️ 📄 Rasm -> PDF", callback_data="tool_img2pdf"),
            InlineKeyboardButton(text="📦 ZIP Arxiv Yaratish / Ochish", callback_data="tool_zip")
        ]
    ])

def get_pdf_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📑 Bitta Jamlangan PDF", callback_data="pdf_combined"),
            InlineKeyboardButton(text="📄 Har Biri Alohida PDF", callback_data="pdf_single")
        ]
    ])

def get_text_tools_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔤 Lotin ➡️ Kirill", callback_data="tool_lat2cyr"),
            InlineKeyboardButton(text="🔤 Kirill ➡️ Lotin", callback_data="tool_cyr2lat")
        ],
        [
            InlineKeyboardButton(text="🗣 Matndan Ovoz (TTS)", callback_data="tool_tts"),
            InlineKeyboardButton(text="🌐 Aqlli Tarjimon", callback_data="tool_trans")
        ],
        [
            InlineKeyboardButton(text="🖋 Imlo & Grammatika", callback_data="tool_gram")
        ]
    ])

def get_translator_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek tiliga", callback_data="trans_uz"),
            InlineKeyboardButton(text="🇷🇺 Rus tiliga", callback_data="trans_ru")
        ],
        [
            InlineKeyboardButton(text="🇬🇧 Ingliz tiliga", callback_data="trans_en"),
            InlineKeyboardButton(text="🇹🇷 Turk tiliga", callback_data="trans_tr")
        ],
        [
            InlineKeyboardButton(text="🇸🇦 Arab tiliga", callback_data="trans_ar")
        ]
    ])

def get_utility_tools_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 QR Kod Yaratish", callback_data="tool_genqr"),
            InlineKeyboardButton(text="🔍 QR Kodni O'qish", callback_data="tool_readqr")
        ],
        [
            InlineKeyboardButton(text="💱 Valyuta Kurslari (CBU)", callback_data="tool_currency")
        ]
    ])
