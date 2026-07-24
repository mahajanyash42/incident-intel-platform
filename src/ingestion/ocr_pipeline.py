"""
Runs OCR on error screenshots to extract text, then feeds that text into
retrieval to prove the screenshot -> OCR -> RAG chain works end to end.
"""
import os
import sys
import glob

import pytesseract
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.rag.retrieval import search_similar_incidents

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image(image_path: str) -> str:
    """Runs OCR on a single image and returns the extracted text."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()


def process_all_screenshots():
    """
    Processes every screenshot in data/sample_screenshots/, runs OCR,
    and tests retrieval against the extracted text.
    """
    screenshots_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "sample_screenshots"
    )
    image_files = glob.glob(os.path.join(screenshots_dir, "*.png"))

    for image_path in sorted(image_files):
        filename = os.path.basename(image_path)
        print(f"=== {filename} ===")

        extracted_text = extract_text_from_image(image_path)
        print(f"OCR extracted text:\n{extracted_text}\n")

        if not extracted_text:
            print("  (no text extracted, skipping retrieval test)\n")
            continue

        output = search_similar_incidents(extracted_text, top_k=2)
        confidence_label = "STRONG MATCH" if output["has_strong_match"] else "NO STRONG MATCH"
        print(f"Retrieval confidence: {confidence_label}")
        for r in output["results"]:
            print(f"  [{r['score']:.3f}] {r['incident_id']} — {r['title']}")
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    process_all_screenshots()