import os
import aiohttp
import qrcode
from pathlib import Path
from PIL import Image
from core.config import TEMP_DIR, logger
from modules.ai.ai_engine import analyze_image_with_ai

def generate_qr_code(data: str, output_path: str) -> bool:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        return True
    except Exception as e:
        logger.error(f"QR generate error: {e}")
        return False

async def read_qr_code(user_id: int, image_path: str) -> str:
    prompt = "Ushbu rasmdagi QR kodni o'qing va uning ichidagi havola (URL) yoki matnni to'liq chiqarib bering. Faqat ichidagi ma'lumotni yozing."
    return await analyze_image_with_ai(user_id, image_path, prompt)

async def get_cbu_currency_rates() -> dict:
    url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rates = {}
                    for item in data:
                        ccy = item.get("Ccy")
                        if ccy in ["USD", "EUR", "RUB", "KZT", "CNY", "TRY"]:
                            rates[ccy] = {
                                "rate": item.get("Rate"),
                                "diff": item.get("Diff"),
                                "date": item.get("Date"),
                                "name": item.get("CcyNm_UZ")
                            }
                    return {"success": True, "rates": rates}
                return {"success": False, "error": f"Status: {resp.status}"}
    except Exception as e:
        logger.error(f"CBU Currency error: {e}")
        return {"success": False, "error": str(e)}
