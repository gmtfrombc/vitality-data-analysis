"""
Services package for the AAA Learning System.

This package contains service classes that handle business logic
for the learning and correction system.
"""

from .correction_service import CorrectionService, CorrectionSession, IntentPattern
from .dashboard_service import DashboardService, DashboardHealthStatus

__all__ = [
    "CorrectionService",
    "CorrectionSession",
    "IntentPattern",
    "DashboardService",
    "DashboardHealthStatus",
]
