# app/query_refinement/clarification_workflow.py


class ClarificationWorkflow:
    """
    Handles clarification question display and processing, decoupled from UI.
    """

    def __init__(self, engine, workflow_state):
        self.engine = engine
        self.workflow_state = workflow_state

    def get_clarifying_questions(self, intent, query_text):
        """
        Return list of clarifying questions for this query/intent.
        """
        # Example: Use slot-based clarifier to get questions
        from app.utils.intent_clarification import clarifier

        needs_clarification, questions = clarifier.get_specific_clarification(
            intent, query_text
        )
        return needs_clarification, questions

    def process_clarification_response(self, intent, clarification_text):
        """
        Apply user clarification to intent, update workflow state as needed.
        """
        if not clarification_text.strip():
            return False, "Please provide clarification."
        # Example: Add clarification context to intent
        if hasattr(intent, "raw_query"):
            intent.raw_query += f"\n\nAdditional context: {clarification_text.strip()}"
        # ... add any additional logic here ...
        self.workflow_state.mark_clarification_complete()
        return True, None

    def needs_clarification(self, intent, query_text):
        """
        Return True if the query intent requires clarification (missing info or ambiguous).
        This method encapsulates the business logic for when to prompt for clarification,
        using the slot-based clarifier.
        """
        from app.utils.intent_clarification import clarifier

        needs_clarification, _ = clarifier.get_specific_clarification(
            intent, query_text
        )
        return needs_clarification

    def extract_active_inactive_preference(self, clarification_text):
        """
        Analyzes the user's clarification response for active/inactive patient filtering.
        Returns 'active', 'inactive', or None if no preference found.
        This encapsulates the business logic for interpreting clarification results.
        """
        text = clarification_text.strip().lower()
        if "all patient" in text or "inactive" in text:
            return "inactive"
        elif "active" in text and "only" in text:
            return "active"
        return None
