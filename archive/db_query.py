import sys as _sys

# Import the real implementation from the app package
_mod = __import__("app.db_query", fromlist=["*"])

# Register the module under the old import path so statements like
# ``import db_query`` or ``from db_query import query_dataframe`` continue to work.
_sys.modules[__name__] = _mod

# Re-export public attributes to the current namespace for ``from db_query import X``
globals().update(_mod.__dict__)
