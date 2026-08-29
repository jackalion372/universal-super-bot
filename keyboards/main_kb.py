from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from core.config import ADMIN_IDS

def get_main_menu_keyboard(user_id: int = 0):
    keyboard = [
        [
            KeyboardButton(text="📥 Media Yuklash"),
            KeyboardButton(text="🎵 Shazam & Musiqa")
        ],
        [
            KeyboardButton(text="🧠 AI Yordamchi"),
            KeyboardButton(text="🎓 Student Studiyasi")
        ],
        [
            KeyboardButton(text="🎨 Rasm Vositalari"),
            KeyboardButton(text="📄 Fayl & PDF")
        ],
        [
            KeyboardButton(text="✍️ Matn & Til"),
            KeyboardButton(text="🛠 Kundalik Asboblar")
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
