import panel as pn
import sys
import pytest

print(f"Python version: {sys.version}")
print(f"Panel version: {pn.__version__}")

# Initialize Panel
pn.extension()

# Determine available spinner indicator
SpinnerCls = getattr(pn.indicators, "Spinner", None)
if SpinnerCls is None:
    SpinnerCls = getattr(pn.indicators, "LoadingSpinner", None)

if SpinnerCls is None:
    pytest.skip(
        "No spinner indicator available in this Panel version", allow_module_level=True
    )

# Create spinner instance
spinner = SpinnerCls(value=True, width=25, height=25)

# Create simple layout (used only if executed as a script)
layout = pn.Column(
    pn.pane.Markdown("# Spinner Test"),
    spinner,
    pn.pane.Markdown("The spinner should appear above this text"),
)

# Show the app directly when running `python test_spinner.py`
if __name__ == "__main__":
    print("Displaying spinner test...")
    layout.show()
