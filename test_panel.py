import panel as pn
import sys

print(f"Python version: {sys.version}")
print(f"Panel version: {pn.__version__}")

# Create a simple Panel app
pn.extension()

# Create a basic layout
layout = pn.Column(
    pn.pane.Markdown("# Panel Test"),
    pn.widgets.TextInput(name="Test Input", placeholder="Enter text here"),
    pn.widgets.Button(name="Test Button", button_type="primary")
)

# Show the app
if __name__ == "__main__":
    print("Displaying Panel app...")
    layout.show()
