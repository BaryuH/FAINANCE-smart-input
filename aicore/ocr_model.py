"""
Vintern OCR model wrapper with singleton pattern.
Loads model once at startup, reuses for all OCR requests.
"""

import torch
import torchvision.transforms as T
from PIL import Image
from transformers import AutoModel, AutoTokenizer
from typing import Optional
import logging

from .config import OCR_MODEL_NAME, OCR_CONFIG, OCR_PROMPT

logger = logging.getLogger(__name__)


class VinternOCR:
    """Singleton wrapper for Vintern OCR model."""

    _instance: Optional["VinternOCR"] = None
    _initialized: bool = False

    def __new__(cls) -> "VinternOCR":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        logger.info("Initializing Vintern OCR model...")

        # PreTrainedModel.post_init writes self.all_tied_weights_keys.  In
        # transformers >= 4.36 that name is a read-only property, so if the
        # InternVL cached model file hasn't been patched yet we need to swallow
        # that AttributeError here.
        try:
            from transformers.modeling_utils import PreTrainedModel as PTM

            _orig = PTM.post_init

            def _patched(self, *args, **kwargs):
                try:
                    _orig(self, *args, **kwargs)
                except AttributeError as e:
                    if "all_tied_weights_keys" not in str(e):
                        raise

            PTM.post_init = _patched
        except Exception:
            pass

        # ImageNet normalization constants
        self.imagenet_mean = (0.485, 0.456, 0.406)
        self.imagenet_std = (0.229, 0.224, 0.225)
        self.input_size = OCR_CONFIG["image_size"]
        self.max_num = OCR_CONFIG["max_num_patches"]

        # Load model
        self.model = (
            AutoModel.from_pretrained(
                OCR_MODEL_NAME,
                torch_dtype=torch.float16,
                trust_remote_code=OCR_CONFIG["trust_remote_code"],
                use_flash_attn=OCR_CONFIG["use_flash_attn"],
            )
            .eval()
            .cuda()
        )

        self.model = self.model.to(torch.float16)

        self.tokenizer = AutoTokenizer.from_pretrained(
            OCR_MODEL_NAME,
            trust_remote_code=OCR_CONFIG["trust_remote_code"],
            use_fast=False,
        )

        # Ensure tokenizer has a pad token id to avoid Transformers warning
        # about setting pad_token_id to eos_token_id:None during generation.
        try:
            if self.tokenizer.pad_token_id is None:
                if getattr(self.tokenizer, "eos_token_id", None) is not None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                elif getattr(self.tokenizer, "bos_token_id", None) is not None:
                    self.tokenizer.pad_token = self.tokenizer.bos_token
        except Exception:
            # If tokenizer is unusual, leave it unchanged; downstream we'll
            # set a pad_token_id in the generation config as a fallback.
            pass

        self._initialized = True
        logger.info("Vintern OCR model loaded successfully!")

    @classmethod
    def get_instance(cls) -> "VinternOCR":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _build_transform(self, input_size: int) -> T.Compose:
        """Build image transformation pipeline."""
        return T.Compose(
            [
                T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
                T.Resize(
                    (input_size, input_size), interpolation=T.InterpolationMode.BICUBIC
                ),
                T.ToTensor(),
                T.Normalize(mean=self.imagenet_mean, std=self.imagenet_std),
            ]
        )

    def _find_closest_aspect_ratio(
        self,
        aspect_ratio: float,
        target_ratios: list,
        width: int,
        height: int,
        image_size: int,
    ) -> tuple:
        """Find the closest aspect ratio from target ratios."""
        best_ratio_diff = float("inf")
        best_ratio = (1, 1)
        area = width * height

        for ratio in target_ratios:
            target_aspect = ratio[0] / ratio[1]
            diff = abs(aspect_ratio - target_aspect)
            if diff < best_ratio_diff or (
                diff == best_ratio_diff
                and area > 0.5 * image_size * image_size * ratio[0] * ratio[1]
            ):
                best_ratio_diff = diff
                best_ratio = ratio
        return best_ratio

    def _dynamic_preprocess(
        self,
        image: Image.Image,
        min_num: int = 1,
        max_num: int = 12,
        image_size: int = 448,
        use_thumbnail: bool = True,
    ) -> list:
        """Dynamically preprocess image into patches."""
        orig_w, orig_h = image.size
        aspect_ratio = orig_w / orig_h

        target_ratios = sorted(
            (i, j)
            for n in range(min_num, max_num + 1)
            for i in range(1, n + 1)
            for j in range(1, n + 1)
            if i * j >= min_num and i * j <= max_num
        )

        target_aspect = self._find_closest_aspect_ratio(
            aspect_ratio, target_ratios, orig_w, orig_h, image_size
        )

        blocks = target_aspect[0] * target_aspect[1]
        target_w = image_size * target_aspect[0]
        target_h = image_size * target_aspect[1]

        resized = image.resize((target_w, target_h))
        patches = []

        for i in range(blocks):
            box = (
                (i % (target_w // image_size)) * image_size,
                (i // (target_w // image_size)) * image_size,
                ((i % (target_w // image_size)) + 1) * image_size,
                ((i // (target_w // image_size)) + 1) * image_size,
            )
            patches.append(resized.crop(box))

        if use_thumbnail and len(patches) != 1:
            patches.append(image.resize((image_size, image_size)))

        return patches

    def _load_image(self, image: Image.Image) -> torch.Tensor:
        """Load and preprocess image for model input."""
        transform = self._build_transform(self.input_size)
        patches = self._dynamic_preprocess(
            image, image_size=self.input_size, use_thumbnail=True, max_num=self.max_num
        )
        pixel_values = torch.stack([transform(p) for p in patches])
        return pixel_values

    def extract_text(self, image_input: str | Image.Image) -> str:
        """
        Extract text from image.

        Args:
            image_input: Either file path (str) or PIL Image object

        Returns:
            Extracted text string
        """
        try:
            # Load image
            if isinstance(image_input, str):
                image = Image.open(image_input).convert("RGB")
            else:
                image = image_input.convert("RGB")

            # Preprocess
            pixel_values = self._load_image(image)

            # Ensure input tensor is on the same device and has the same dtype
            try:
                model_param = next(self.model.parameters())
                device = model_param.device
                dtype = model_param.dtype
            except StopIteration:
                device = torch.device("cuda")
                dtype = torch.float16

            pixel_values = pixel_values.to(device=device, dtype=dtype)

            # Generation config
            gen_config = {
                "max_new_tokens": 1024,
                "do_sample": False,
                "num_beams": 3,
                "repetition_penalty": 3.5,
            }

            # Ensure pad_token_id is set
            pad_id = (
                getattr(self.tokenizer, "pad_token_id", None)
                or getattr(self.tokenizer, "eos_token_id", None)
                or getattr(self.tokenizer, "bos_token_id", None)
                or 0
            )
            gen_config["pad_token_id"] = pad_id

            question = "<image>\n" + OCR_PROMPT

            with torch.no_grad():
                result = self.model.chat(
                    self.tokenizer,
                    pixel_values,
                    question,
                    gen_config,
                )
                response = result if isinstance(result, str) else result.get("text", "")

            return response.strip()

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}", exc_info=True)
            return ""

    def extract_text_batch(
        self, image_inputs: list[str] | list[Image.Image]
    ) -> list[str]:
        """
        Extract text from multiple images in batch (sequential).

        Args:
            image_inputs: List of file paths (str) or PIL Image objects

        Returns:
            List of extracted text strings
        """
        results: list[str] = [""] * len(image_inputs)

        try:
            # Load all images
            batch_images: list[Image.Image] = []
            for img_input in image_inputs:
                if isinstance(img_input, str):
                    image = Image.open(img_input).convert("RGB")
                else:
                    image = img_input.convert("RGB")
                batch_images.append(image)

            # Get model device and dtype
            try:
                model_param = next(self.model.parameters())
                device = model_param.device
                dtype = model_param.dtype
            except StopIteration:
                device = torch.device("cuda")
                dtype = torch.float16

            # Generation config
            gen_config = {
                "max_new_tokens": 1024,
                "do_sample": False,
                "num_beams": 3,
                "repetition_penalty": 3.5,
            }
            pad_id = (
                getattr(self.tokenizer, "pad_token_id", None)
                or getattr(self.tokenizer, "eos_token_id", None)
                or getattr(self.tokenizer, "bos_token_id", None)
                or 0
            )
            gen_config["pad_token_id"] = pad_id

            question = "<image>\n" + OCR_PROMPT

            # Process images one at a time (max_num_patches controls patch count per image)
            for idx, image in enumerate(batch_images):
                pixel_values = self._load_image(image)
                pixel_values = pixel_values.to(device=device, dtype=dtype)

                with torch.no_grad():
                    response = self.model.chat(
                        self.tokenizer,
                        pixel_values,
                        question,
                        gen_config,
                    )

                if isinstance(response, str):
                    results[idx] = response.strip()
                elif isinstance(response, dict):
                    results[idx] = response.get("text", "").strip()
                else:
                    results[idx] = str(response).strip()

        except Exception as e:
            logger.error(f"OCR batch extraction failed: {e}", exc_info=True)

        return results