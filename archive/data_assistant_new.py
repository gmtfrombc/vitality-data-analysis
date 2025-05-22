"""
Data Analysis Assistant Page

Simple import wrapper to load the data assistant page from our refactored module.
This maintains backward compatibility with the page routing in the app.
"""

from app.data_assistant import data_assistant_page

# Export the page function
__all__ = ["data_assistant_page"]
