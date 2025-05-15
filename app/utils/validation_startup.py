from __future__ import annotations

"""Validation system startup shim.

This module simply re-exports :pyfunc:`initialize_validation_system` from the
archived implementation to satisfy imports in *run.py* until the refactor is
complete.
"""

# type: ignore[F401]
from app.utils.utils_archive.validation_startup import initialize_validation_system

__all__ = ["initialize_validation_system"]
