"""Tests for the AI fallback functionality in condition_mapper."""

from unittest.mock import patch, MagicMock

from app.utils.condition_mapper import ConditionMapper


class TestConditionMapperAIFallback:
    """Tests for the AI-powered ICD-10 lookup functionality."""

    def test_should_ask_clarifying_question(self):
        """Test the clarifying question logic."""
        mapper = ConditionMapper()

        # Mock get_canonical_condition to return None for unknown conditions
        with patch.object(mapper, "get_canonical_condition", return_value=None):
            # With no OpenAI client
            mapper.client = None
            assert mapper.should_ask_clarifying_question("unknown condition") is True

            # With OpenAI client available
            mapper.client = MagicMock()
            assert mapper.should_ask_clarifying_question("unknown condition") is True

        # Known condition should not need clarification
        with patch.object(
            mapper, "get_canonical_condition", return_value="hypertension"
        ):
            assert mapper.should_ask_clarifying_question("high blood pressure") is False

    @patch("app.utils.condition_mapper.OpenAI")
    def test_lookup_icd_codes_with_ai_successful(self, mock_openai):
        """Test successful AI-powered ICD-10 code lookup."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock successful response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_function_call = MagicMock()
        mock_function_call.name = "provide_icd10_codes"
        mock_function_call.arguments = """
        {
            "condition_name": "Migraine with aura",
            "icd10_codes": ["G43.1", "G43.10", "G43.11"],
            "description": "Migraine headache with sensory disturbances",
            "confidence": 0.95
        }
        """
        mock_message.function_call = mock_function_call
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response

        # Create mapper with mocked OpenAI client
        mapper = ConditionMapper()
        mapper.client = mock_client

        # Test the function
        result = mapper.lookup_icd_codes_with_ai("migraine with aura")

        # Verify results
        assert result == ["G43.1", "G43.10", "G43.11"]
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.utils.condition_mapper.OpenAI")
    def test_lookup_icd_codes_with_ai_low_confidence(self, mock_openai):
        """Test AI lookup with low confidence score."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock low confidence response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_function_call = MagicMock()
        mock_function_call.name = "provide_icd10_codes"
        mock_function_call.arguments = """
        {
            "condition_name": "Vague symptom",
            "icd10_codes": ["R99"],
            "description": "Unspecified condition",
            "confidence": 0.3
        }
        """
        mock_message.function_call = mock_function_call
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response

        # Create mapper with mocked OpenAI client
        mapper = ConditionMapper()
        mapper.client = mock_client

        # Test the function
        result = mapper.lookup_icd_codes_with_ai("vague symptom")

        # Verify results - should return empty list for low confidence
        assert result == []
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.utils.condition_mapper.OpenAI")
    def test_lookup_icd_codes_with_ai_error(self, mock_openai):
        """Test error handling during AI lookup."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API error")

        # Create mapper with mocked OpenAI client
        mapper = ConditionMapper()
        mapper.client = mock_client

        # Test the function
        result = mapper.lookup_icd_codes_with_ai("test condition")

        # Verify results - should gracefully handle errors
        assert result == []
        mock_client.chat.completions.create.assert_called_once()

    def test_get_icd_codes_fallback(self):
        """Test the fallback to AI lookup in get_icd_codes method."""
        mapper = ConditionMapper()

        # Mock direct lookup to fail
        with patch.object(mapper, "get_canonical_condition", return_value=None):
            # Mock AI lookup to succeed
            test_codes = ["Z99.9", "Z99.8"]
            with patch.object(
                mapper, "lookup_icd_codes_with_ai", return_value=test_codes
            ):
                codes = mapper.get_icd_codes("unknown condition")
                assert codes == test_codes

            # Mock AI lookup to fail
            with patch.object(mapper, "lookup_icd_codes_with_ai", return_value=[]):
                codes = mapper.get_icd_codes("completely unknown condition")
                assert codes == []
