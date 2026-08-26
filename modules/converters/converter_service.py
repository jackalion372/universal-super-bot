import os
import zipfile
from pathlib import Path
from PIL import Image
from core.config import TEMP_DIR, logger

def images_to_pdf(image_paths: list[str], output_pdf_path: str) -> bool:
    try:
        images = []
        for p in image_paths:
            img = Image.open(p).convert('RGB')
            images.append(img)
            
        if not images:
            return False
            
        images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
        return True
    except Exception as e:
        logger.error(f"Images to PDF error: {e}")
        return False

def image_to_single_pdf(image_path: str, output_pdf_path: str) -> bool:
    try:
        img = Image.open(image_path).convert('RGB')
        img.save(output_pdf_path)
        return True
    except Exception as e:
        logger.error(f"Single image to PDF error: {e}")
        return False

def create_zip_archive(file_paths: list[str], output_zip_path: str) -> bool:
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in file_paths:
                zipf.write(file, arcname=os.path.basename(file))
        return True
    except Exception as e:
        logger.error(f"Create ZIP error: {e}")
        return False

def extract_zip_archive(zip_path: str, extract_dir: str) -> list[str]:
    try:
        extracted = []
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(extract_dir)
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    extracted.append(os.path.join(root, f))
        return extracted
    except Exception as e:
        logger.error(f"Extract ZIP error: {e}")
        return []
