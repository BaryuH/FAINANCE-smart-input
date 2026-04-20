"""
aicore module for Slacker-AI expense tracker.
Provides unified OCR, ASR, and LLM parsing services with model preloading.
"""

from .pipeline import AIPipeline

__all__ = ["AIPipeline"]
