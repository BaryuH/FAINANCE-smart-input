"""
Gipformer ASR wrapper for aicore pipeline.

This module wraps the existing `gipformer/infer_onnx.py` helpers to
provide a singleton ASR class compatible with the existing `SherpaASR`
API (`get_instance()`, `transcribe()`, `transcribe_bytes()`).
"""

from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GipformerASR:
    _instance: Optional["GipformerASR"] = None
    _initialized: bool = False

    def __new__(cls) -> "GipformerASR":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        quantize: str = "fp32",
        num_threads: int = 4,
        decoding_method: str = "modified_beam_search",
    ) -> None:
        if self._initialized:
            return

        logger.info("Initializing Gipformer ASR runtime (ONNX)")

        # Import the gipformer inference helpers from the project folder
        from importlib import util
        import importlib
        from pathlib import Path

        gip_dir = Path(__file__).resolve().parent.parent / "gipformer"
        infer_src = gip_dir / "infer_onnx.py"
        spec = util.spec_from_file_location("gip_infer_onnx", str(infer_src))
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Download model files (fp32 by default)
        self.module = module
        self.model_paths = module.download_model(quantize)

        # Create recognizer
        self.recognizer = module.create_recognizer(
            self.model_paths, num_threads=num_threads, decoding_method=decoding_method
        )

        self.sample_rate = (
            module.SAMPLE_RATE if hasattr(module, "SAMPLE_RATE") else 16000
        )
        self._initialized = True
        logger.info("Gipformer ASR runtime is ready")

    @classmethod
    def get_instance(cls) -> "GipformerASR":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def transcribe(self, audio_path: str) -> str:
        try:
            return self.module.transcribe(self.recognizer, audio_path)
        except Exception as e:
            logger.error("Audio transcription failed path=%s error=%s", audio_path, e, exc_info=True)
            return ""

    def transcribe_bytes(self, audio_bytes: bytes, format: str = "wav") -> str:
        try:
            # Save bytes to temp file then call transcribe
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            text = self.transcribe(tmp_path)

            # cleanup
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

            return text
        except Exception as e:
            logger.error("Audio-bytes transcription failed format=%s error=%s", format, e, exc_info=True)
            return ""
