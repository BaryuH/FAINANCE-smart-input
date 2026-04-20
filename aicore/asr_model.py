"""
ASR integration for AI-core.

This module now supports only the Gipformer provider. It lazily
initializes `GipformerASR` from `aicore.gipformer_asr` so that
dependencies are loaded only when needed.
"""

from typing import Any
import logging

from .config import ASR_CONFIG

logger = logging.getLogger(__name__)


def get_asr_instance() -> Any:
    """Return the Gipformer ASR singleton instance.

    Raises RuntimeError if initialization fails.
    """
    provider = ASR_CONFIG.get("provider", "gipformer")
    if provider != "gipformer":
        logger.warning("ASR provider is not 'gipformer' — forcing gipformer usage")

    try:
        # Lazy import so gipformer-related deps are only required when used
        from .gipformer_asr import GipformerASR

        return GipformerASR.get_instance()
    except Exception as e:
        logger.exception("Failed to initialize GipformerASR")
        raise RuntimeError("Failed to initialize Gipformer ASR") from e
