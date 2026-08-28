import os
import io
from pathlib import Path
from PIL import Image
try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader, PdfWriter = None, None

from core.config import TEMP_DIR, logger

def convert_images_to_pdf(image_paths: list, output_pdf_path: str) -> str:
    """Rasmlar ro'yxatini bitta tartibli PDF hujjatiga birlashtiradi"""
    if not image_paths:
        raise ValueError("Rasmlar ro'yxati bo'sh!")
    
    images = []
    for img_path in image_paths:
        try:
            img = Image.open(img_path).convert("RGB")
            images.append(img)
        except Exception as e:
            logger.error(f"Image load error {img_path}: {e}")
            
    if not images:
        raise ValueError("Yaroqli rasmlar topilmadi!")
        
    first_image = images[0]
    rest_images = images[1:] if len(images) > 1 else []
    first_image.save(output_pdf_path, save_all=True, append_images=rest_images)
    return output_pdf_path

def extract_pdf_text_to_string(pdf_path: str) -> str:
    """PDF fayldan barcha sahifalar matnini ajratib oladi"""
    if not PdfReader:
        raise ImportError("pypdf kutubxonasi o'rnatilmagan!")
        
    reader = PdfReader(pdf_path)
    extracted = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            extracted.append(f"--- Sahifa {i+1} ---\n{text.strip()}\n")
            
    return "\n".join(extracted) if extracted else "⚠️ PDF hujjatda o'qiladigan matn topilmadi (u faqat rasmlardan iborat bo'lishi mumkin)."
