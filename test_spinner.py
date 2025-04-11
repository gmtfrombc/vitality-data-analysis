import panel as pn
import sys
import time

print(f"Python version: {sys.version}")
print(f"Panel version: {pn.__version__}")

# Initialize Panel
pn.extension()

# Create spinner
spinner = pn.indicators.Spinner(value=True, width=25, height=25)

# Create simple layout
layout = pn.Column(
    pn.pane.Markdown("# Spinner Test"),
    spinner,
    pn.pane.Markdown("The spinner should appear above this text")
)

# Show the app
if __name__ == "__main__":
    print("Displaying spinner test...")
    layout.show()
