from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from core.config import ADMIN_IDS

def get_main_menu_keyboard(user_id: int = 0):
    keyboard = [
        [
            KeyboardButton(text="🎓 Student Studiyasi")
        ],
        [
            KeyboardButton(text="📥 Media Studiya"),
            KeyboardButton(text="🧠 AI Studiya")
        ],
        [
            KeyboardButton(text="📄 Hujjat & PDF Studiyasi"),
            KeyboardButton(text="🎨 Rasm, Matn & Utilitlar")
        ],
        [
            KeyboardButton(text="📩 Adminga Murojaat")
        ]
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(text="👑 Admin Panel")])
        
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    keyboard = [[KeyboardButton(text="🔙 Bosh menyu")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
