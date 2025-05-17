"""Condition mapping utilities for ICD-10 codes.

This module provides functionality to map between clinical condition terms
and ICD-10 codes, supporting the intent classification system.
"""

from __future__ import annotations

import logging
import os
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import re
from openai import OpenAI

from app.reference_ranges import REFERENCE_RANGES

logger = logging.getLogger(__name__)


@dataclass
class ConditionMapping:
    """Represents a clinical condition with its ICD-10 codes and synonyms."""

    canonical: str
    codes: List[str]
    description: str
    synonyms: List[str]


class ConditionMapper:
    """Maps clinical condition terms to ICD-10 codes and vice versa."""

    def __init__(self, mapping_file: str = None):
        """Initialize the condition mapper with the specified mapping file.

        Args:
            mapping_file: Path to the YAML mapping file. If None, uses the default path.
        """
        if mapping_file is None:
            # Default path is relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            mapping_file = os.path.join(current_dir, "condition_mappings.yaml")

        self.load_mappings(mapping_file)
        self.client = None
        try:
            # Initialize OpenAI client if API key is available
            if os.getenv("OPENAI_API_KEY"):
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")

    def load_mappings(self, mapping_file: str) -> None:
        """Load condition mappings from a YAML file.

        Args:
            mapping_file: Path to the YAML mapping file
        """
        self.mappings: Dict[str, ConditionMapping] = {}
        self.term_to_canonical: Dict[str, str] = {}
        self.codes_to_canonical: Dict[str, str] = {}

        try:
            with open(mapping_file, "r") as f:
                data = yaml.safe_load(f)

            if not data or "conditions" not in data:
                logger.warning(f"No conditions found in mapping file: {mapping_file}")
                return

            for condition in data["conditions"]:
                canonical = condition.get("canonical")
                if not canonical:
                    logger.warning(
                        f"Skipping condition without canonical name: {condition}"
                    )
                    continue

                codes = condition.get("codes", [])
                description = condition.get("description", "")
                synonyms = condition.get("synonyms", [])

                # Create mapping object
                mapping = ConditionMapping(
                    canonical=canonical,
                    codes=codes,
                    description=description,
                    synonyms=synonyms,
                )

                # Store mapping by canonical name
                self.mappings[canonical] = mapping

                # Index all terms (canonical + synonyms) to find by any term
                self.term_to_canonical[canonical.lower()] = canonical
                for synonym in synonyms:
                    self.term_to_canonical[synonym.lower()] = canonical

                # Index codes for reverse lookup
                for code in codes:
                    self.codes_to_canonical[code] = canonical

            logger.info(f"Loaded {len(self.mappings)} condition mappings")

        except Exception as e:
            logger.error(f"Error loading condition mappings: {e}")
            # Initialize empty to avoid None errors
            self.mappings = {}
            self.term_to_canonical = {}
            self.codes_to_canonical = {}

    def get_canonical_condition(self, term: str) -> Optional[str]:
        """Get the canonical condition name for a given term.

        Args:
            term: The condition term or synonym to look up

        Returns:
            The canonical condition name if found, None otherwise
        """
        if not term:
            return None

        # Normalize by converting to lowercase
        term_lower = term.lower()

        # Check for exact match in our mapping
        if term_lower in self.term_to_canonical:
            return self.term_to_canonical[term_lower]

        # Check for partial matches (substring)
        for known_term, canonical in self.term_to_canonical.items():
            if term_lower in known_term or known_term in term_lower:
                return canonical

        # Special handling for BMI values
        bmi_match = re.search(r"bmi\s+(\d+\.?\d*)", term_lower)
        if bmi_match:
            bmi_value = float(bmi_match.group(1))

            if bmi_value >= REFERENCE_RANGES["bmi_morbid_obesity"]:
                # Morbid obesity for BMI >= 40
                return "morbid_obesity"
            elif bmi_value >= REFERENCE_RANGES["bmi_obese"]:
                # Regular obesity for BMI 30-39.9
                return "obesity"
            elif bmi_value >= REFERENCE_RANGES["bmi_overweight"]:
                # Overweight for BMI 25-29.9
                return "overweight"

        return None

    def get_icd_codes(self, condition: str) -> List[str]:
        """Get all ICD-10 codes associated with a condition.

        Args:
            condition: The condition term or synonym to look up

        Returns:
            List of ICD-10 codes for the condition
        """
        canonical = self.get_canonical_condition(condition)
        if canonical and canonical in self.mappings:
            codes: List[str] = list(self.mappings[canonical].codes)

            # SPECIAL-CASE: include morbid obesity codes when querying generic obesity.
            # Clinicians often expect "obesity" counts to include morbid / severe obesity.
            if canonical == "obesity" and "morbid_obesity" in self.mappings:
                codes.extend(self.mappings["morbid_obesity"].codes)

            if canonical == "obesity" and "overweight" in self.mappings:
                codes.extend(self.mappings["overweight"].codes)

            # Remove duplicates while preserving order
            deduped: List[str] = []
            for c in codes:
                if c not in deduped:
                    deduped.append(c)
            return deduped

        # Try AI-powered lookup as fallback if no match found
        icd_codes = self.lookup_icd_codes_with_ai(condition)
        if icd_codes:
            return icd_codes

        return []

    def get_description(self, condition: str) -> str:
        """Get the description for a condition.

        Args:
            condition: The condition term or synonym to look up

        Returns:
            Description string if found, empty string otherwise
        """
        canonical = self.get_canonical_condition(condition)
        if canonical and canonical in self.mappings:
            return self.mappings[canonical].description
        return ""

    def get_all_codes_as_sql_list(self, condition: str) -> str:
        """Get all ICD-10 codes for a condition as a comma-separated SQL list.

        Args:
            condition: The condition term or synonym to look up

        Returns:
            String with SQL-formatted list of codes (e.g., "'E11.9', 'E11.8'")
            or empty string if no codes found
        """
        codes = self.get_icd_codes(condition)
        if not codes:
            return ""

        return ", ".join(f"'{code}'" for code in codes)

    def lookup_icd_codes_with_ai(self, condition_term: str) -> List[str]:
        """Use OpenAI to look up ICD-10 codes for conditions not in our dictionary.

        Args:
            condition_term: The clinical condition term to look up

        Returns:
            List of ICD-10 codes, or empty list if lookup failed or client not available
        """
        if not self.client:
            logger.warning("OpenAI client not available for ICD-10 lookup")
            return []

        logger.info(f"Using AI to look up ICD-10 codes for: {condition_term}")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical coding assistant. Provide the most relevant ICD-10 codes for the given condition.",
                    },
                    {
                        "role": "user",
                        "content": f"What are the ICD-10 codes for '{condition_term}'?",
                    },
                ],
                functions=[
                    {
                        "name": "provide_icd10_codes",
                        "description": "Provide ICD-10 codes for a medical condition",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "condition_name": {
                                    "type": "string",
                                    "description": "The standardized name of the condition",
                                },
                                "icd10_codes": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of ICD-10 codes for the condition (e.g., ['E11.9', 'E11.8'])",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Brief description of the condition",
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "Confidence level from 0.0 to 1.0",
                                },
                            },
                            "required": ["condition_name", "icd10_codes"],
                        },
                    }
                ],
                function_call={"name": "provide_icd10_codes"},
                temperature=0.1,
                max_tokens=500,
            )

            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "provide_icd10_codes":
                try:
                    args = json.loads(function_call.arguments)
                    codes = args.get("icd10_codes", [])
                    confidence = args.get("confidence", 0.0)
                    logger.info(
                        f"AI returned {len(codes)} ICD-10 codes with confidence {confidence}"
                    )

                    # Only use codes if confidence is reasonable
                    if confidence >= 0.6:
                        return codes
                    else:
                        logger.warning(
                            f"Low confidence ({confidence}) for AI ICD-10 lookup: {condition_term}"
                        )
                        return []
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to parse AI response for ICD-10 lookup: {function_call.arguments}"
                    )

            return []

        except Exception as e:
            logger.error(f"Error during AI ICD-10 lookup: {e}")
            return []

    def should_ask_clarifying_question(self, condition_term: str) -> bool:
        """Determine if we should ask a clarifying question for this condition.

        Args:
            condition_term: The condition term to check

        Returns:
            True if we should ask for clarification, False otherwise
        """
        # If the term is in our dictionary, no need to clarify
        if self.get_canonical_condition(condition_term):
            return False

        # If the condition is unknown and we have no OpenAI client, we should clarify
        if not self.client:
            return True

        # If multiple potential matches exist, we should clarify
        # This would require implementing a fuzzy search for potential matches
        # For now, we'll just return True for any unknown condition
        return True


# Create a singleton instance
condition_mapper = ConditionMapper()
