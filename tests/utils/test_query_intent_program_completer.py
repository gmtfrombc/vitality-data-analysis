from app.utils.query_intent import _normalise_field_name


def test_program_completer_synonyms():
    """Verify synonyms are normalised to the canonical 'program_completer'."""
    synonyms = [
        "program completer",
        "program completers",
        "program finisher",
        "program finishers",
        "completer",
        "finishers",
    ]
    for term in synonyms:
        assert (
            _normalise_field_name(term) == "program_completer"
        ), f"{term} not mapped correctly"
