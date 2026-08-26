import os
import re
import asyncio
from pathlib import Path
import edge_tts
from core.config import TEMP_DIR, logger
from modules.ai.ai_engine import ask_gemini_chat

CYR_TO_LAT = {
    'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v', 'Г': 'G', 'г': 'g',
    'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e', 'Ё': 'Yo', 'ё': 'yo', 'Ж': 'J', 'ж': 'j',
    'З': 'Z', 'z': 'z', 'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
    'Л': 'L', 'l': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n', 'О': 'O', 'о': 'o',
    'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r', 'С': 'S', 'с': 's', 'Т': 'T', 'т': 't',
    'У': 'U', 'у': 'u', 'Ф': 'F', 'ф': 'f', 'Х': 'X', 'х': 'x', 'Ц': 'Ts', 'ц': 'ts',
    'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Ъ': "'", 'ъ': "'", 'Ь': "", 'ь': "",
    'Э': 'E', 'э': 'e', 'Ю': 'Yu', 'ю': 'yu', 'Я': 'Ya', 'я': 'ya',
    'Ў': "O'", 'ў': "o'", 'Қ': 'Q', 'қ': 'q', 'Ғ': "G'", 'ғ': "g'", 'Ҳ': 'H', 'ҳ': 'h'
}

LAT_TO_CYR = {
    "O'": 'Ў', "o'": 'ў', "O`": 'Ў', "o`": 'ў', "O’": 'Ў', "o’": 'ў',
    "G'": 'Ғ', "g'": 'ғ', "G`": 'Ғ', "g`": 'ғ', "G’": 'Ғ', "g’": 'ғ',
    "Sh": 'Ш', "sh": 'ш', "SH": 'Ш',
    "Ch": 'Ч', "ch": 'ч', "CH": 'Ч',
    "Yo": 'Ё', "yo": 'ё', "YO": 'Ё',
    "Yu": 'Ю', "yu": 'ю', "YU": 'Ю',
    "Ya": 'Я', "ya": 'я', "YA": 'Я',
    "Ts": 'Ц', "ts": 'ц', "TS": 'Ц',
    'A': 'А', 'a': 'а', 'B': 'Б', 'b': 'б', 'V': 'В', 'v': 'в', 'G': 'Г', 'g': 'г',
    'D': 'Д', 'd': 'д', 'E': 'Е', 'e': 'е', 'J': 'Ж', 'j': 'ж', 'Z': 'З', 'z': 'з',
    'I': 'И', 'i': 'и', 'Y': 'Й', 'y': 'й', 'K': 'К', 'k': 'к', 'L': 'Л', 'l': 'л',
    'M': 'М', 'm': 'м', 'N': 'Н', 'n': 'н', 'O': 'О', 'o': 'о', 'P': 'П', 'p': 'п',
    'R': 'Р', 'r': 'р', 'S': 'С', 's': 'с', 'T': 'Т', 't': 'т', 'U': 'У', 'u': 'у',
    'F': 'Ф', 'f': 'ф', 'X': 'Х', 'x': 'х', 'Q': 'Қ', 'q': 'қ', 'H': 'Ҳ', 'h': 'ҳ'
}

def cyrillic_to_latin(text: str) -> str:
    res = text
    for cyr, lat in CYR_TO_LAT.items():
        res = res.replace(cyr, lat)
    return res

def latin_to_cyrillic(text: str) -> str:
    res = text
    for lat, cyr in LAT_TO_CYR.items():
        res = res.replace(lat, cyr)
    return res

VOICES = {
    "uz": "uz-UZ-MadinaNeural",
    "uz_male": "uz-UZ-SardorNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "en": "en-US-JennyNeural"
}

async def text_to_speech(text: str, output_path: str, lang: str = "uz") -> bool:
    try:
        voice = VOICES.get(lang, "uz-UZ-MadinaNeural")
        
        # Ruscha harflar ko'p bo'lsa avtomatik rus ovozini tanlash
        if bool(re.search(r'[а-яА-ЯёЁ]', text)) and lang == "uz":
            voice = "ru-RU-SvetlanaNeural"
        elif all(ord(c) < 128 for c in text.replace(" ", "").replace("\n", "")) and len(text) > 10 and lang == "uz":
            # Agar sof inglizcha bo'lsa
            if any(w in text.lower() for w in ["the", "is", "are", "hello", "how", "what"]):
                voice = "en-US-JennyNeural"

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Edge TTS error: {e}")
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='tr')
            tts.save(output_path)
            return True
        except Exception:
            return False

async def smart_translate(user_id: int, text: str, target_lang: str = "o'zbek") -> str:
    prompt = f"Ushbu matnni {target_lang} tiliga eng yuqori sifatli, tabiiy va ravon qilib tarjima qilib bering:\n\n{text}"
    return await ask_gemini_chat(user_id, prompt)

async def check_grammar(user_id: int, text: str) -> str:
    prompt = f"Ushbu matndagi imlo va grammatik xatolarni tekshirib, to'g'rilangan variantini va xatolarni tushuntirib bering:\n\n{text}"
    return await ask_gemini_chat(user_id, prompt)
