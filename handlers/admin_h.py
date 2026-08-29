import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from core.config import ADMIN_IDS, DB_PATH
from core.database import (
    get_detailed_stats,
    get_channels,
    add_channel,
    remove_channel,
    get_setting,
    set_setting,
    get_all_user_ids,
    ban_user,
    unban_user,
    set_user_mode,
    get_user_mode
)

router = Router()

ADMIN_REPLY_TARGET = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_admin_main_keyboard():
    force_status = "🟢 Yoqilgan" if get_setting("force_sub") == "1" else "🔴 O'chirilgan"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 To'liq Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Xabar Tarqatish (Rassilka)", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text=f"🔒 Majburiy Obuna: {force_status}", callback_data="admin_toggle_forcesub")
        ],
        [
            InlineKeyboardButton(text="➕ Kanal Qo'shish", callback_data="admin_add_channel"),
            InlineKeyboardButton(text="📋 Kanallar Ro'yxati", callback_data="admin_list_channels")
        ],
        [
            InlineKeyboardButton(text="💾 Baza Zaxirasi (DB)", callback_data="admin_backup_db"),
            InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
        ]
    ])

@router.message(Command("admin"))
@router.message(F.text == "👑 Admin Panel")
async def cmd_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ **Siz bot administratori emassiz.**")
        return
        
    set_user_mode(message.from_user.id, "general")
    welcome_admin = (
        "👑 **Assalomu alaykum, Hurmatli Admin!**\n\n"
        "Boshqaruv paneliga xush kelibsiz. Quyidagi menyu orqali botni to'liq boshqarishingiz mumkin:"
    )
    await message.answer(welcome_admin, parse_mode="Markdown", reply_markup=get_admin_main_keyboard())

@router.message(Command("stats"))
async def cmd_stats_direct(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = get_detailed_stats()
    text = (
        "📊 **Botning Jonli Statistikasi:**\n\n"
        f"👥 **Jami a'zolar:** `{stats['total_users']}` ta\n"
        f"🆕 **Bugun qo'shilganlar:** `{stats['today_users']}` ta\n"
        f"⚡️ **Faol foydalanuvchilar (24 soat):** `{stats['active_users']}` ta\n\n"
        f"📥 **Jami yuklab olishlar:** `{stats['total_downloads']}` ta\n"
        f"🧠 **AI so'rovlari:** `{stats['total_ai']}` ta\n"
        f"🎵 **Shazam / Musiqa:** `{stats['total_shazam']}` ta"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_admin_main_keyboard())

# ==================== STATS ====================

@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    stats = get_detailed_stats()
    text = (
        "📊 **Botning Jonli Statistikasi:**\n\n"
        f"👥 **Jami a'zolar:** `{stats['total_users']}` ta\n"
        f"🆕 **Bugun qo'shilganlar:** `{stats['today_users']}` ta\n"
        f"⚡️ **Faol foydalanuvchilar (24 soat):** `{stats['active_users']}` ta\n\n"
        f"📥 **Jami yuklab olishlar:** `{stats['total_downloads']}` ta\n"
        f"🧠 **AI so'rovlari:** `{stats['total_ai']}` ta\n"
        f"🎵 **Shazam / Musiqa:** `{stats['total_shazam']}` ta"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_admin_main_keyboard())

# ==================== FORCE SUB TOGGLE & CHANNELS ====================

@router.callback_query(F.data == "admin_toggle_forcesub")
async def handle_toggle_forcesub(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    current = get_setting("force_sub", "0")
    new_val = "0" if current == "1" else "1"
    set_setting("force_sub", new_val)
    
    status_str = "yoqildi 🟢" if new_val == "1" else "o'chirildi 🔴"
    await callback.answer(f"Majburiy obuna {status_str}!", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_list_channels")
async def handle_list_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    channels = get_channels()
    if not channels:
        await callback.message.edit_text(
            "📋 **Hozircha hech qanday kanal ulanmagan.**\n\nKanal qo'shish uchun '➕ Kanal Qo'shish' tugmasini bosing.",
            reply_markup=get_admin_main_keyboard()
        )
        return
        
    kb = []
    for ch in channels:
        kb.append([
            InlineKeyboardButton(text=f"📢 {ch['channel_title']}", url=ch['channel_url']),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_ch_{ch['channel_id']}")
        ])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    
    await callback.message.edit_text("📋 **Ulangan Kanallar Ro'yxati:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("del_ch_"))
async def handle_delete_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    ch_id = callback.data.replace("del_ch_", "")
    remove_channel(ch_id)
    await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
    await handle_list_channels(callback)

@router.callback_query(F.data == "admin_add_channel")
async def handle_add_channel_prompt(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    set_user_mode(callback.from_user.id, "admin_add_channel_mode")
    text = (
        "➕ **Yangi kanal qo'shish:**\n\n"
        "1. Botni kanalingizga **Admin (administrator)** qilib qo'shing.\n"
        "2. Keyin kanal havolasini yoki username'ini yuboring:\n"
        "*(Format: `@kanal_nomi` yoki `https://t.me/kanal_nomi`)*"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_backup_db")
async def handle_backup_db(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    await callback.answer("Baza yuklanmoqda...")
    if os.path.exists(DB_PATH):
        db_file = FSInputFile(DB_PATH, filename="bot_database_backup.db")
        await callback.message.answer_document(document=db_file, caption="💾 **Ma'lumotlar bazasi zaxira nusxasi (Backup)**")

@router.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("👑 **Admin Boshqaruv Paneli:**", reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_close")
async def handle_admin_close(callback: CallbackQuery):
    await callback.message.delete()

# ==================== BROADCAST (RASSILKA) ====================

@router.message(Command("broadcast"))
@router.callback_query(F.data == "admin_broadcast")
async def handle_broadcast_prompt(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return
        
    set_user_mode(user_id, "admin_broadcast_mode")
    msg_txt = (
        "📢 **Rassilka Rejimi:**\n\nBarcha bot foydalanuvchilariga yubormoqchi bo'lgan xabaringizni (matn, rasm, video yoki forward post) yuboring:\n\n*(Bekor qilish uchun /cancel yozing)*"
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(msg_txt, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(msg_txt, parse_mode="Markdown")

@router.message(F.text | F.photo | F.video)
async def handle_broadcast_execution(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if get_user_mode(message.from_user.id) != "admin_broadcast_mode":
        return
        
    if message.text == "/cancel":
        set_user_mode(message.from_user.id, "general")
        await message.answer("❌ Rassilka bekor qilindi.")
        return
        
    set_user_mode(message.from_user.id, "general")
    user_ids = get_all_user_ids()
    total = len(user_ids)
    
    status = await message.answer(f"🚀 **Rassilka boshlandi...**\nJami foydalanuvchilar: {total} ta")
    
    sent_count = 0
    blocked_count = 0
    
    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            sent_count += 1
            await asyncio.sleep(0.04)
        except Exception:
            blocked_count += 1
            
    await status.edit_text(
        f"✅ **Rassilka muvaffaqiyatli yakunlandi!**\n\n"
        f"📤 **Yuborildi:** `{sent_count}` ta\n"
        f"🚫 **Yetib bormadi (bloklagan):** `{blocked_count}` ta\n"
        f"👥 **Jami:** `{total}` ta",
        parse_mode="Markdown"
    )

# ==================== ADD CHANNEL INPUT HANDLER ====================

@router.message(F.text)
async def handle_channel_text(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if get_user_mode(message.from_user.id) != "admin_add_channel_mode":
        return
        
    raw = message.text.strip()
    username = raw.replace("https://t.me/", "").replace("@", "")
    ch_target = f"@{username}"
    
    try:
        chat = await bot.get_chat(ch_target)
        title = chat.title or ch_target
        url = f"https://t.me/{username}"
        ch_id = str(chat.id)
        
        if add_channel(ch_id, title, url):
            set_user_mode(message.from_user.id, "general")
            await message.answer(f"✅ **Kanal muvaffaqiyatli qo'shildi!**\n\n📢 **Nomi:** {title}\n🔗 **Havola:** {url}", parse_mode="Markdown")
        else:
            await message.answer("⚠️ Bu kanal allaqachon qo'shilgan.")
    except Exception as e:
        await message.answer(f"❌ Kanalni tekshirib bo'lmadi: {e}\nIltimos, bot kanalda Admin ekanligiga ishonch hosil qiling.")

# ==================== ADMIN REPLY TO USER FEEDBACK ====================

@router.callback_query(F.data.startswith("reply_user_"))
async def handle_reply_user_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    target_id = int(callback.data.replace("reply_user_", ""))
    ADMIN_REPLY_TARGET[callback.from_user.id] = target_id
    set_user_mode(callback.from_user.id, "admin_reply_user_mode")
    
    await callback.message.answer(f"✍️ **Foydalanuvchiga (ID: `{target_id}`) javobingizni yozing:**", parse_mode="Markdown")
    await callback.answer()

@router.message(F.text)
async def handle_admin_reply_send(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if get_user_mode(message.from_user.id) != "admin_reply_user_mode":
        return
        
    target_id = ADMIN_REPLY_TARGET.get(message.from_user.id)
    if not target_id:
        set_user_mode(message.from_user.id, "general")
        await message.answer("⚠️ Foydalanuvchi topilmadi.")
        return
        
    try:
        reply_txt = (
            "📩 **Admin javobi:**\n\n"
            f"{message.text}\n\n"
            "💬 *Savolingiz bo'lsa, 'Adminga Murojaat' orqali yana yozishingiz mumkin.*"
        )
        await bot.send_message(chat_id=target_id, text=reply_txt, parse_mode="Markdown")
        await message.answer(f"✅ **Javob foydalanuvchiga (ID: `{target_id}`) muvaffaqiyatli yetkazildi!**")
    except Exception as e:
        await message.answer(f"❌ Xabarni yetkazishda xatolik: {e}")
    finally:
        set_user_mode(message.from_user.id, "general")

