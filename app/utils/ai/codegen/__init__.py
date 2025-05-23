# codegen package for modular code generation logic

from .basic import generate_basic_code
from .trend import generate_trend
from .top_n import generate_top_n, generate_histogram
from .comparison import generate_comparison_code
from .change import generate_relative_change_code
from .correlation import generate_correlation_code
from .fallback import generate_fallback_code

__all__ = [
    "generate_basic_code",
    "generate_trend",
    "generate_top_n",
    "generate_histogram",
    "generate_comparison_code",
    "generate_relative_change_code",
    "generate_correlation_code",
    "generate_fallback_code",
]
