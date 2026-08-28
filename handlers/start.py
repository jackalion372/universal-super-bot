from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent
)
import urllib.parse
from keyboards.main_kb import get_main_menu_keyboard, get_cancel_keyboard
from keyboards.inline_kb import (
    get_media_tools_keyboard,
    get_file_tools_keyboard,
    get_text_tools_keyboard,
    get_utility_tools_keyboard
)
from core.config import ADMIN_IDS
from core.database import (
    upsert_user,
    set_user_mode,
    get_user_mode,
    get_setting,
    get_channels,
    is_banned
)
from modules.text_tools.text_service import latin_to_cyrillic, cyrillic_to_latin

router = Router()

async def check_user_subscription(bot: Bot, user_id: int) -> tuple[bool, list]:
    if user_id in ADMIN_IDS:
        return True, []
        
    force_sub = get_setting("force_sub", "0")
    if force_sub != "1":
        return True, []
        
    channels = get_channels()
    if not channels:
        return True, []
        
    unsubscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["channel_id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed.append(ch)
        except Exception:
            pass
            
    return len(unsubscribed) == 0, unsubscribed

@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start_or_menu(message: Message, bot: Bot):
    user = message.from_user
    
    if is_banned(user.id):
        await message.answer("⛔️ **Siz botdan foydalanishdan bloklangansiz.**")
        return
        
    upsert_user(user.id, user.first_name, user.last_name or "", user.username or "")
    set_user_mode(user.id, "general")
    
    is_subbed, unsubs = await check_user_subscription(bot, user.id)
    if not is_subbed:
        kb = []
        for ch in unsubs:
            kb.append([InlineKeyboardButton(text=f"📢 {ch['channel_title']}", url=ch['channel_url'])])
        kb.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub_again")])
        
        await message.answer(
            "⚠️ **Botdan to'liq foydalanish uchun quyidagi kanallarga a'zo bo'ling:**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        return
    
    is_adm = user.id in ADMIN_IDS
    adm_badge = " *(Siz Bosh Admin siz 👑)*" if is_adm else ""
    
    welcome_text = (
        f"🔥 **Assalomu alaykum, {user.first_name}!**{adm_badge}\n\n"
        f"🌟 **Universal Super Bot** sahifasi yangilandi!\n\n"
        f"📥 **Media Yuklash:** Instagram, TikTok, YouTube, Pinterest, Likee, Snapchat.\n"
        f"🎵 **Shazam:** Ovoz, video yoki audio tashlasangiz, qo'shiqni topib beraman.\n"
        f"🧠 **Gemini AI:** Har qanday savol, rasm, PDF, Word yoki Excel hujjat tahlili.\n"
        f"🎨 **Vositalar:** Fon o'chirish, OCR, Rasm/Video siqish, Lotin-Kirill, TTS, QR-kod, Valyuta.\n"
        f"📩 **Adminga Murojaat:** Savollaringiz bo'lsa to'g'ridan-to'g'ri adminga yozishingiz mumkin.\n\n"
        f"🚀 *Kerakli bo'limni tanlang yoki to'g'ridan-to'g'ri havola/savol yuboring!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard(user.id))

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "💡 **Bot Buyruqlari va Qo'llanma:**\n\n"
        "• `/start` — Botni qayta ishga tushirish va yangilash\n"
        "• `/menu` — Asosiy menyuni ochish va yangilash\n"
        "• `/downloader` — Media yuklash bo'limi\n"
        "• `/shazam` — Musiqa qidiruv va Shazam\n"
        "• `/ai` — Gemini AI suhbatdoshi\n"
        "• `/reset` — AI suhbat xotirasini tozalash\n"
        "• `/tools` — Rasm va media vositalari\n"
        "• `/contact` — Adminga murojaat qilish\n"
    )
    if message.from_user.id in ADMIN_IDS:
        help_text += "\n👑 **Admin Buyruqlari:**\n• `/admin` — Boshqaruv paneli\n• `/stats` — Jonli statistika"
        
    await message.answer(help_text, parse_mode="Markdown")

@router.callback_query(F.data == "check_sub_again")
async def handle_check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    is_subbed, unsubs = await check_user_subscription(bot, user_id)
    if is_subbed:
        await callback.answer("✅ Rahmat! Barcha kanallarga obuna bo'ldingiz.", show_alert=True)
        await callback.message.delete()
        await callback.message.answer(
            f"🎉 **Xush kelibsiz, {callback.from_user.first_name}!** Botdan bemalol foydalanishingiz mumkin.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        await callback.answer("❌ Hali barcha kanallarga a'zo bo'lmadingiz. Iltimos, a'zo bo'ling!", show_alert=True)

@router.message(F.text == "🔙 Bosh menyu")
async def back_to_main(message: Message):
    set_user_mode(message.from_user.id, "general")
    await message.answer("🏠 **Bosh menyuga qaytdingiz.**", parse_mode="Markdown", reply_markup=get_main_menu_keyboard(message.from_user.id))

# ==================== DIRECT COMMANDS & GROUPED MENUS ====================

@router.message(Command("downloader"))
@router.message(F.text.in_({"📥 Media Yuklash", "📥 Media Studiya"}))
async def menu_downloader(message: Message):
    set_user_mode(message.from_user.id, "downloader")
    info = (
        "📥 **Media Studiya Bo'limi**\n\n"
        "Quyidagi tarmoqlardan video yoki post havolasini (link) yuboring:\n"
        "• 📸 **Instagram:** Post, Reels, Carousel, Stories\n"
        "• 🎵 **TikTok:** Suv belgisiz HD video + Audio\n"
        "• ▶️ **YouTube:** Video, Shorts + MP3 Audio\n"
        "• 📌 **Pinterest:** HD Video va 4K Foto\n"
        "• 👻 **Snapchat & Likee:** Sifatli video\n\n"
        "👉 *Havolani (link) shu yerga yuboring:*"
    )
    await message.answer(info, parse_mode="Markdown")

@router.message(Command("shazam"))
@router.message(F.text == "🎵 Shazam & Musiqa")
async def menu_shazam(message: Message):
    set_user_mode(message.from_user.id, "shazam")
    info = (
        "🎵 **Shazam & Musiqa Qidiruv**\n\n"
        "Quyidagilardan birini yuboring:\n"
        "1. 🎤 **Ovozli xabar** yoki 📹 **Video xabar** (dumaloq video)\n"
        "2. 🎶 **Audio yoki Video fayl** (bot qo'shiqni avtomatik topadi)\n"
        "3. ✍️ **Qo'shiq nomi, ijrochi yoki qo'shiq so'zlari**ni yozing\n\n"
        "👉 *Qidirmoqchi bo'lgan ovoz yoki matnni yuboring:*"
    )
    await message.answer(info, parse_mode="Markdown")

@router.message(Command("ai"))
@router.message(F.text.in_({"🧠 AI Yordamchi", "🧠 AI Studiya"}))
async def menu_ai(message: Message):
    set_user_mode(message.from_user.id, "ai")
    info = (
        "🧠 **Google Gemini AI Studiya**\n\n"
        "Men sizga quyidagilarda yordam bera olaman:\n"
        "💬 Har qanday mavzuda suhbat va savol-javob\n"
        "💻 Mukammal dasturlash va kodlar yozish\n"
        "🎤 Ovozli savollarni tinglab, tushunish\n"
        "🖼 Rasm va fotosuratlarni chuqur tahlil qilish\n"
        "📄 PDF, Word, Excel va kod fayllarini o'qish\n\n"
        "🔄 Xotirani tozalash uchun: **/reset**\n\n"
        "👉 *Savolingizni yozing yoki rasm/fayl yuboring:*"
    )
    await message.answer(info, parse_mode="Markdown")

@router.message(F.text.in_({"📄 Fayl & PDF", "📄 Hujjat & PDF Studiyasi"}))
async def menu_file_tools(message: Message):
    await message.answer("📄 **Hujjat va PDF Studiyasi:**\nKerakli xizmatni tanlang:", reply_markup=get_file_tools_keyboard())

@router.message(Command("tools"))
@router.message(F.text.in_({"🎨 Rasm Vositalari", "🎨 Rasm, Matn & Utilitlar"}))
async def menu_media_tools(message: Message):
    await message.answer("🎨 **Rasm, Matn va Kundalik Utilitlar:**\nKerakli bo'limni tanlang:", reply_markup=get_media_tools_keyboard())


# ==================== ADMINGA MUROJAAT (FEEDBACK) ====================

@router.message(Command("contact"))
@router.message(F.text == "📩 Adminga Murojaat")
async def menu_feedback(message: Message):
    set_user_mode(message.from_user.id, "feedback_mode")
    text = (
        "📩 **Adminga Murojaat Bo'limi:**\n\n"
        "Taklif, savol yoki shikoyatingizni bitta xabarda yozib yuboring.\n"
        "Xabaringiz to'g'ridan-to'g'ri bot administratoriga yetkaziladi va sizga shu yerda javob beriladi.\n\n"
        "*(Bekor qilish uchun '🔙 Bosh menyu' tugmasini bosing)*"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())

@router.message(F.text, lambda msg: get_user_mode(msg.from_user.id) == "feedback_mode")
async def handle_user_feedback_send(message: Message, bot: Bot):
    user = message.from_user
    user_text = message.text.strip()
    
    if user_text in ["🔙 Bosh menyu", "/cancel"]:
        set_user_mode(user.id, "general")
        await message.answer("🏠 Bosh menyuga qaytdingiz.", reply_markup=get_main_menu_keyboard(user.id))
        return
        
    set_user_mode(user.id, "general")
    username_str = f"@{user.username}" if user.username else "mavjud emas"
    
    admin_notify = (
        "📩 **Yangi Murojaat Keldi!**\n\n"
        f"👤 **Foydalanuvchi:** {user.full_name} ({username_str})\n"
        f"🆔 **ID:** `{user.id}`\n\n"
        f"💬 **Xabar:**\n{user_text}"
    )
    
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Javob Berish", callback_data=f"reply_user_{user.id}")]
    ])
    
    for adm_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=adm_id, text=admin_notify, parse_mode="Markdown", reply_markup=reply_kb)
        except Exception:
            pass
            
    await message.answer(
        "✅ **Xabaringiz adminga yetkazildi!**\nTez orada javob qaytaramiz. Rahmat!",
        reply_markup=get_main_menu_keyboard(user.id)
    )

# ==================== INLINE MODE (@Mr_nafi_bot ...) ====================

@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    results = []
    
    if not query:
        # Bo'sh qidiruvda eslatma
        results.append(InlineQueryResultArticle(
            id="hint_0",
            title="💡 Istalgan matn yozing...",
            description="Lotin/Kirill o'girish yoki QR kod yaratish uchun matn yozing",
            input_message_content=InputTextMessageContent(message_text="🤖 @Mr_nafi_bot orqali tezkor vositalar!")
        ))
        await inline_query.answer(results, cache_time=1)
        return
        
    # 1. Kirillcha o'girish
    cyr = latin_to_cyrillic(query)
    results.append(InlineQueryResultArticle(
        id="cyr_1",
        title="🔤 Kirillcha shakli",
        description=cyr[:80],
        input_message_content=InputTextMessageContent(message_text=cyr)
    ))
    
    # 2. Lotincha o'girish
    lat = cyrillic_to_latin(query)
    results.append(InlineQueryResultArticle(
        id="lat_2",
        title="🔤 Lotincha shakli",
        description=lat[:80],
        input_message_content=InputTextMessageContent(message_text=lat)
    ))
    
    # 3. QR Kod yaratish
    encoded_q = urllib.parse.quote(query)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_q}"
    results.append(InlineQueryResultPhoto(
        id="qr_3",
        photo_url=qr_url,
        thumbnail_url=qr_url,
        caption=f"📱 **QR Kod:** `{query[:40]}`\n\n🤖 @Mr_nafi_bot",
        parse_mode="Markdown"
    ))
    
    await inline_query.answer(results, cache_time=5)
