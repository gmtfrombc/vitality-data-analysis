import argparse
import re
from pathlib import Path

TESTS_ROOT = Path("tests/triage")  # auto-created when script runs

HEADER = (
    "# Auto-generated regression test\n"
    "#\n"
    "# This test was created from negative clinician feedback.\n"
    "# Fill in the expected assertions to make it actionable.\n\n"
)


DEF_TEMPLATE = """
from app.data_assistant import DataAnalysisAssistant

def {test_name}():
    assistant = DataAnalysisAssistant()
    assistant.query_text = {query_literal}

    # Act
    assistant._process_query()

    # TODO: Replace with specific assertions, e.g.:
    # assert assistant.analysis_result['value'] == EXPECTED
    assert assistant.analysis_result is not None
"""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:40]  # keep slug reasonably short


def create_test_file(question: str) -> Path:
    TESTS_ROOT.mkdir(parents=True, exist_ok=True)
    test_name = f"test_{slugify(question)}"
    file_path = TESTS_ROOT / f"{test_name}.py"

    if file_path.exists():
        print(f"Test file {file_path} already exists – skipping.")
        return file_path

    code = HEADER + DEF_TEMPLATE.format(
        test_name=test_name, query_literal=repr(question)
    )
    file_path.write_text(code)
    print(f"Created {file_path.relative_to(Path.cwd())}")
    return file_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate a pytest template for a specific question."
    )
    parser.add_argument(
        "question", help="Natural-language question to turn into a test"
    )
    args = parser.parse_args()

    create_test_file(args.question)


if __name__ == "__main__":
    main()
