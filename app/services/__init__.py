"""
Services package for the AAA Learning System.

This package contains service classes that handle business logic
for the learning and correction system.
"""

from .correction_service import CorrectionService, CorrectionSession, IntentPattern

__all__ = ["CorrectionService", "CorrectionSession", "IntentPattern"]
