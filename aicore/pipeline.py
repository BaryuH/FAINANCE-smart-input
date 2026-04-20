"""
Unified AI pipeline service.
Coordinates OCR, ASR, and LLM parsing with model preloading.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from PIL import Image

from .ocr_model import VinternOCR
from .asr_model import get_asr_instance
from .llm_parser import get_llm_parser
from .json_utils import extract_price_from_text

logger = logging.getLogger(__name__)


class AIPipeline:
    """
    Unified AI pipeline for processing images and audio.
    All models are preloaded on initialization to avoid reload overhead.
    """

    def __init__(self) -> None:
        logger.info("Initializing AI Pipeline with model preloading...")

        # Preload all models
        self.ocr = VinternOCR.get_instance()
        self.asr = get_asr_instance()
        self.llm = get_llm_parser()

        logger.info("AI Pipeline initialized - all models loaded!")

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process image input through OCR and expense parsing.

        Args:
            image_path: Path to image file

        Returns:
            JSON result with category, price, note, and metadata
        """
        try:
            logger.info(f"Processing image: {image_path}")

            # Step 1: Extract text from image using OCR
            extracted_text = self.ocr.extract_text(image_path)
            logger.info(f"OCR extracted text: {extracted_text}")

            if not extracted_text:
                return {
                    "status": "error",
                    "message": "Không thể trích xuất văn bản từ ảnh",
                    "input_type": "image",
                    "raw_text": "",
                    "result": {"category": "khác", "price": 0, "note": ""},
                }

            # Step 2: Feed OCR text to Ollama using OCR_PROMPT_2
            result = self.llm.parse_ocr_text(extracted_text)
            logger.info(f"OCR + Ollama parsed result: {result}")

            # Fallback: if parser didn't extract price, try rule-based extraction
            try:
                if isinstance(result, dict) and int(result.get("price", 0)) == 0:
                    detected = extract_price_from_text(extracted_text)
                    if detected and detected > 0:
                        result["price"] = int(detected)
                        if not result.get("note"):
                            result["note"] = extracted_text
            except Exception:
                logger.exception("OCR fallback price extraction failed")

            return {
                "status": "success",
                "input_type": "image",
                "raw_text": extracted_text,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Image processing failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "input_type": "image",
                "raw_text": "",
                "result": {"category": "khác", "price": 0, "note": ""},
            }

    def process_image_batch(self, image_paths: list[str]) -> list[Dict[str, Any]]:
        """
        Process multiple images in batch through OCR.

        Args:
            image_paths: List of paths to image files

        Returns:
            List of JSON results (one per image)
        """
        if not image_paths:
            return []

        try:
            logger.info(f"Processing batch of {len(image_paths)} images")
            extracted_texts = self.ocr.extract_text_batch(image_paths)
        except Exception as e:
            logger.error(
                f"Batch OCR failed, falling back to individual processing: {e}",
                exc_info=True,
            )
            return [self.process_image(path) for path in image_paths]

        results: list[Dict[str, Any]] = []
        for image_path, extracted_text in zip(image_paths, extracted_texts):
            if not extracted_text:
                results.append(
                    {
                        "status": "error",
                        "message": "Không thể trích xuất văn bản từ ảnh",
                        "input_type": "image",
                        "raw_text": "",
                        "result": {"category": "khác", "price": 0, "note": ""},
                    }
                )
                continue

            result = self.llm.parse_ocr_text(extracted_text)
            try:
                if isinstance(result, dict) and int(result.get("price", 0)) == 0:
                    detected = extract_price_from_text(extracted_text)
                    if detected and detected > 0:
                        result["price"] = int(detected)
                        if not result.get("note"):
                            result["note"] = extracted_text
            except Exception:
                logger.exception("Batch OCR fallback price extraction failed")

            results.append(
                {
                    "status": "success",
                    "input_type": "image",
                    "raw_text": extracted_text,
                    "result": result,
                }
            )

        logger.info(f"Batch OCR complete: {len(results)} results")
        return results

    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Process audio input through ASR and expense parsing.

        Args:
            audio_path: Path to audio file

        Returns:
            JSON result with category, price, note, and metadata
        """
        try:
            logger.info(f"Processing audio: {audio_path}")

            # Step 1: Transcribe audio to text using ASR
            transcribed_text = self.asr.transcribe(audio_path)
            logger.info(f"ASR transcribed text: {transcribed_text}")

            if not transcribed_text:
                return {
                    "status": "error",
                    "message": "Không thể nhận dạng giọng nói",
                    "input_type": "audio",
                    "raw_text": "",
                    "result": {"category": "khác", "price": 0, "note": ""},
                }

            # Step 2: Normalize text (strip and lowercase)
            normalized_text = transcribed_text.strip().lower()
            logger.info(f"Normalized text: {normalized_text}")

            # Step 3: Parse normalized text with LLM
            result = self.llm.parse_expense(normalized_text)
            logger.info(f"LLM parsed result: {result}")

            # Fallback: if LLM didn't extract a price, try rule-based numeric extraction
            try:
                if isinstance(result, dict) and int(result.get("price", 0)) == 0:
                    detected = extract_price_from_text(normalized_text)
                    if detected and detected > 0:
                        logger.info(f"Fallback price detected from text: {detected}")
                        result["price"] = int(detected)
                        # if note empty, keep normalized text as note
                        if not result.get("note"):
                            result["note"] = normalized_text
            except Exception:
                logger.exception("Fallback price extraction failed")

            return {
                "status": "success",
                "input_type": "audio",
                "raw_text": transcribed_text,
                "normalized_text": normalized_text,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Audio processing failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "input_type": "audio",
                "raw_text": "",
                "result": {"category": "khác", "price": 0, "note": ""},
            }

    def process_audio_bytes(
        self, audio_bytes: bytes, format: str = "wav"
    ) -> Dict[str, Any]:
        """
        Process audio from bytes.

        Args:
            audio_bytes: Raw audio bytes
            format: Audio format (wav, m4a, mp3, etc.)

        Returns:
            JSON result with category, price, note, and metadata
        """
        try:
            logger.info(
                f"Processing audio bytes ({len(audio_bytes)} bytes, format: {format})"
            )

            # Step 1: Transcribe audio bytes to text
            transcribed_text = self.asr.transcribe_bytes(audio_bytes, format)
            logger.info(f"ASR transcribed text: {transcribed_text}")

            if not transcribed_text:
                return {
                    "status": "error",
                    "message": "Không thể nhận dạng giọng nói",
                    "input_type": "audio",
                    "raw_text": "",
                    "result": {"category": "khác", "price": 0, "note": ""},
                }

            # Step 2: Normalize text (strip and lowercase)
            normalized_text = transcribed_text.strip().lower()

            # Step 3: Parse with LLM
            result = self.llm.parse_expense(normalized_text)

            # Fallback: if LLM didn't extract a price, try rule-based numeric extraction
            try:
                if isinstance(result, dict) and int(result.get("price", 0)) == 0:
                    detected = extract_price_from_text(normalized_text)
                    if detected and detected > 0:
                        logger.info(f"Fallback price detected from text: {detected}")
                        result["price"] = int(detected)
                        if not result.get("note"):
                            result["note"] = normalized_text
            except Exception:
                logger.exception("Fallback price extraction failed")

            return {
                "status": "success",
                "input_type": "audio",
                "raw_text": transcribed_text,
                "normalized_text": normalized_text,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Audio bytes processing failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "input_type": "audio",
                "raw_text": "",
                "result": {"category": "khác", "price": 0, "note": ""},
            }

    def process_text(self, text: str) -> Dict[str, Any]:
        """
        Process direct text input through expense parsing.

        Args:
            text: Expense description text

        Returns:
            JSON result with category, price, note, and metadata
        """
        try:
            logger.info(f"Processing text: {text}")

            # Normalize text
            normalized_text = text.strip().capitalize()

            # Parse with LLM
            result = self.llm.parse_expense(normalized_text)

            # Fallback: if LLM didn't extract a price, try rule-based numeric extraction
            try:
                if isinstance(result, dict) and int(result.get("price", 0)) == 0:
                    detected = extract_price_from_text(normalized_text)
                    if detected and detected > 0:
                        logger.info(f"Fallback price detected from text: {detected}")
                        result["price"] = int(detected)
                        if not result.get("note"):
                            result["note"] = normalized_text
            except Exception:
                logger.exception("Fallback price extraction failed")

            return {
                "status": "success",
                "input_type": "text",
                "raw_text": text,
                "normalized_text": normalized_text,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Text processing failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "input_type": "text",
                "raw_text": text,
                "result": {"category": "khác", "price": 0, "note": text},
            }
