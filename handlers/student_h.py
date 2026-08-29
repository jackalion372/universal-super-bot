import os
import asyncio
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from modules.student.student_engine import generate_student_material
from core.database import log_stat, set_user_mode

router = Router()

STUDENT_COMMANDS = {
    "pres": ("💡 Taqdimot (Slayd)", "Taqdimot mavzusini kiriting (Masalan: /pres Sun'iy intellekt kelajagi)"),
    "miq": ("📝 Mustaqil Ish", "Mustaqil ish mavzusini kiriting (Masalan: /miq O'zbekiston iqtisodiyoti)"),
    "ref": ("📄 Referat", "Referat mavzusini kiriting (Masalan: /ref Raqamli iqtisodiyot va IT)"),
    "kurs": ("🎓 Kurs Ishi", "Kurs ishi mavzusini kiriting (Masalan: /kurs Kiberxavfsizlik va ma'lumotlar himoyasi)"),
    "test": ("🧪 Test Savollari", "Qaysi mavzuda test savollari tuzaylik? (Masalan: /test Fizika 9-sinf)"),
    "tezis": ("📑 Tezis", "Tezis mavzusini kiriting (Masalan: /tezis Nanotexnologiyalar rivoji)"),
    "cross": ("🧠 Krossword", "Krossword mavzusini kiriting (Masalan: /cross Biologiya tushunchalari)"),
    "maqola": ("📝 Maqola", "Maqola mavzusini kiriting (Masalan: /maqola Sun'iy intellektning ta'limdagi o'rni)"),
    "insho": ("✏️ Insho / Esse", "Insho mavzusini kiriting (Masalan: /insho Ona tilim — g'ururim)"),
    "infografika": ("📊 Infografika", "Infografika mavzusini kiriting (Masalan: /infografika Quyosh tizimi)"),
    "sayt": ("🌐 Sayt kodi", "Sayt mavzusini kiriting (Masalan: /sayt Shaxsiy portfolio va rezyume)")
}

def get_student_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 Taqdimot (Slayd)", callback_data="stud_pres"),
            InlineKeyboardButton(text="📝 Mustaqil Ish", callback_data="stud_miq")
        ],
        [
            InlineKeyboardButton(text="📄 Referat", callback_data="stud_ref"),
            InlineKeyboardButton(text="🎓 Kurs Ishi", callback_data="stud_kurs")
        ],
        [
            InlineKeyboardButton(text="🧪 Test Savollari", callback_data="stud_test"),
            InlineKeyboardButton(text="📑 Tezis", callback_data="stud_tezis")
        ],
        [
            InlineKeyboardButton(text="📝 Maqola", callback_data="stud_maqola"),
            InlineKeyboardButton(text="✏️ Insho / Esse", callback_data="stud_insho")
        ],
        [
            InlineKeyboardButton(text="📊 Infografika", callback_data="stud_infografika"),
            InlineKeyboardButton(text="🌐 Sayt kodi", callback_data="stud_sayt")
        ]
    ])

@router.message(Command("student"))
@router.message(F.text == "🎓 Student Studiyasi")
async def cmd_student_studio(message: Message):
    welcome_text = (
        "👋 **Assalomu alaykum! Student va Ta'lim Studiyasiga xush kelibsiz!** 🎓\n\n"
        "🤖 *Men Yevropa akademik standartlari bo'yicha tayyor o'quv materiallari tayyorlaydigan maxsus asistintman.*\n\n"
        "📌 **Tezkor Buyruqlar Ro'yxati:**\n"
        "💡 `/pres` — Taqdimot (PowerPoint Slayd) yaratish\n"
        "📝 `/miq` — Mustaqil ish tayyorlash (.docx Word)\n"
        "📄 `/ref` — Referat tayyorlash (.docx Word)\n"
        "🎓 `/kurs` — Kurs ishi yaratish (.docx Word)\n"
        "🧪 `/test` — Variantli Test savollari tuzish\n"
        "📑 `/tezis` — Ilmiy Tezis yaratish\n"
        "🧠 `/cross` — Krossword yaratish\n"
        "📝 `/maqola` — Ilmiy Maqola yaratish\n"
        "✏️ `/insho` — Insho / Esse yozish\n"
        "📊 `/infografika` — Vizual Infografika tuzish\n"
        "🌐 `/sayt` — Sayt HTML/CSS kodini yaratish\n\n"
        "👉 *Kerakli bo'limni quyidagi tugmalardan tanlang yoki buyruq bilan mavzu yuboring:*"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_student_menu_keyboard())

@router.callback_query(F.data.startswith("stud_"))
async def handle_student_callback(callback: CallbackQuery):
    doc_type = callback.data.replace("stud_", "")
    if doc_type in STUDENT_COMMANDS:
        title, guide = STUDENT_COMMANDS[doc_type]
        await callback.message.answer(
            f"✍️ **{title} Bo'limi:**\n\n"
            f"Iltimos, buyruq bilan birga mavzuni yuboring:\n"
            f"👉 `{guide}`",
            parse_mode="Markdown"
        )
    await callback.answer()

@router.message(Command("pres", "miq", "ref", "kurs", "test", "tezis", "cross", "maqola", "insho", "infografika", "sayt"))
async def handle_student_generation_command(message: Message, bot: Bot):
    cmd = message.text.split()[0][1:].lower()
    topic = message.text[len(cmd) + 1:].strip()
    
    if not topic:
        title, guide = STUDENT_COMMANDS.get(cmd, ("Akademik Hujjat", "Mavzuni kiriting"))
        await message.answer(
            f"⚠️ **{title} uchun mavzu kiritilmadi!**\n\n"
            f"Misol uchun: `{guide}`",
            parse_mode="Markdown"
        )
        return
        
    status_msg = await message.answer(f"🎓 **Yevropa akademik standarti bo'yicha tayyorlanmoqda:** `{topic}`\n*Iltimos, biroz kuting...*", parse_mode="Markdown")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    try:
        res = await generate_student_material(message.from_user.id, cmd, topic)
        await status_msg.delete()
        
        if res.get("type") == "file":
            file_path = res["path"]
            file_fmt = res["format"]
            caption = f"🎓 **{topic.title()}**\n\n✅ Yevropa akademik standarti bo'yicha tayyorlandi.\n🤖 @Mr_nafi_bot"
            
            doc_file = FSInputFile(file_path)
            await message.answer_document(document=doc_file, caption=caption, parse_mode="Markdown")
            
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            content = res.get("content", "")
            if len(content) > 4000:
                for chunk in [content[i:i+4000] for i in range(0, len(content), 4000)]:
                    await message.answer(chunk, parse_mode=None)
            else:
                await message.answer(content, parse_mode=None)
                
        log_stat(message.from_user.id, f"student_{cmd}", topic)
    except Exception as e:
        await message.answer(f"❌ **Xatolik yuz berdi:** {e}")
