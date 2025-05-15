"""
State Management for Data Analysis Assistant

This module handles workflow stage transitions and state management for the
data analysis assistant, allowing for better separation of UI and business logic.

The module provides:
1. Constants defining workflow stages and their properties
2. A state machine to manage transitions between workflow stages
3. Methods to validate and control the analysis pipeline flow
4. Stage completion tracking and state flags
"""

import logging
import param

# Configure logging
logger = logging.getLogger("data_assistant.state")


class WorkflowStages:
    """
    Constants for workflow stages.

    This class defines the available stages in the analysis workflow,
    their numeric identifiers, human-readable names, and associated icons.
    It acts as a central reference for all stage-related constants.
    """

    INITIAL = 0  # Initial query input stage
    CLARIFYING = 1  # Clarification questions stage
    CODE_GENERATION = 2  # Code generation stage
    EXECUTION = 3  # Code execution stage
    RESULTS = 4  # Results display stage

    # Human-readable stage names
    STAGE_NAMES = {
        INITIAL: "Input Query",
        CLARIFYING: "Clarify Intent",
        CODE_GENERATION: "Generate Code",
        EXECUTION: "Execute Analysis",
        RESULTS: "Display Results",
    }

    # Stage emoji mappings
    STAGE_EMOJIS = {
        INITIAL: "✏️",
        CLARIFYING: "🔍",
        CODE_GENERATION: "🧠",
        EXECUTION: "⚙️",
        RESULTS: "📊",
    }


class WorkflowState(param.Parameterized):
    """
    Manages workflow state and transitions for the data analysis assistant.

    This class implements a state machine that:
    1. Keeps track of the current stage in the analysis workflow
    2. Validates transitions between stages to ensure proper sequence
    3. Provides methods for advancing through the workflow with validation
    4. Tracks completion status of each stage
    5. Maintains flags for special workflow paths (e.g., clarification)

    The workflow follows a linear progression through the stages defined
    in WorkflowStages, with the possibility of branching for clarification
    when queries are ambiguous.
    """

    current_stage = param.Integer(
        default=WorkflowStages.INITIAL,
        bounds=(WorkflowStages.INITIAL, WorkflowStages.RESULTS),
        doc="Current stage in the analysis workflow (0-4)",
    )

    # State flags for tracking progress
    intent_parsed = param.Boolean(
        default=False, doc="Whether query intent has been successfully parsed"
    )
    clarification_complete = param.Boolean(
        default=False, doc="Whether the clarification process has been completed"
    )
    code_generated = param.Boolean(
        default=False, doc="Whether analysis code has been successfully generated"
    )
    execution_complete = param.Boolean(
        default=False, doc="Whether code execution has completed successfully"
    )
    results_displayed = param.Boolean(
        default=False, doc="Whether results have been displayed to the user"
    )
    needs_clarification = param.Boolean(
        default=False, doc="Whether the current query requires clarification"
    )

    # Current workflow results
    query = param.String(default="", doc="The current query being processed")

    def __init__(self, **params):
        """
        Initialize workflow state.

        Sets up the workflow state machine with default initial values.
        All flags are set to False and the stage is set to INITIAL.
        """
        super().__init__(**params)
        self.reset()

    def reset(self):
        """
        Reset workflow state to initial values.

        Clears all state flags and sets the current stage back to INITIAL.
        This is used when starting a new analysis or clearing the current one.
        """
        self.current_stage = WorkflowStages.INITIAL
        self.intent_parsed = False
        self.clarification_complete = False
        self.code_generated = False
        self.execution_complete = False
        self.results_displayed = False
        self.needs_clarification = False
        self.query = ""
        logger.info("Workflow state reset to initial values")

    def start_query(self, query):
        """
        Start processing a new query.

        Resets the workflow state and stores the new query text.

        Args:
            query (str): The natural language query to process
        """
        self.reset()
        self.query = query
        logger.info(f"Starting new query: {query}")

    def mark_intent_parsed(self, needs_clarification=False):
        """
        Mark that intent has been parsed, optionally requiring clarification.

        Sets the intent_parsed flag and determines whether to move to the
        clarification stage or proceed directly to code generation.

        Args:
            needs_clarification (bool): Whether the query needs clarification

        Returns:
            bool: True if the transition was successful, False otherwise
        """
        self.intent_parsed = True
        self.needs_clarification = needs_clarification

        if needs_clarification:
            self.transition_to(WorkflowStages.CLARIFYING)
        else:
            # Skip clarification and go to code generation
            self.clarification_complete = True
            self.transition_to(WorkflowStages.CODE_GENERATION)

        logger.info(f"Intent parsed, needs clarification: {needs_clarification}")

    def mark_clarification_complete(self):
        """
        Mark that clarification is complete and advance to code generation.

        Sets the clarification_complete flag and transitions to the code
        generation stage if prerequisites are met.

        Returns:
            bool: True if the transition was successful, False otherwise
        """
        if not self.intent_parsed:
            logger.warning("Cannot mark clarification complete: intent not parsed")
            return False

        self.clarification_complete = True
        self.transition_to(WorkflowStages.CODE_GENERATION)
        logger.info("Clarification complete")
        return True

    def mark_code_generated(self):
        """
        Mark that code has been generated and advance to execution.

        Sets the code_generated flag and transitions to the execution
        stage if prerequisites are met.

        Returns:
            bool: True if the transition was successful, False otherwise
        """
        if not (
            self.intent_parsed
            and (self.clarification_complete or not self.needs_clarification)
        ):
            logger.warning("Cannot mark code generated: previous steps incomplete")
            return False

        self.code_generated = True
        self.transition_to(WorkflowStages.EXECUTION)
        logger.info("Code generation complete")
        return True

    def mark_execution_complete(self):
        """
        Mark that execution is complete and advance to results.

        Sets the execution_complete flag and transitions to the results
        stage if prerequisites are met.

        Returns:
            bool: True if the transition was successful, False otherwise
        """
        if not self.code_generated:
            logger.warning("Cannot mark execution complete: code not generated")
            return False

        self.execution_complete = True
        self.transition_to(WorkflowStages.RESULTS)
        logger.info("Execution complete")
        return True

    def mark_results_displayed(self):
        """
        Mark that results have been displayed.

        Sets the results_displayed flag if prerequisites are met.
        This is the final stage in the workflow.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.execution_complete:
            logger.warning("Cannot mark results displayed: execution not complete")
            return False

        self.results_displayed = True
        logger.info("Results displayed")
        return True

    def transition_to(self, target_stage):
        """
        Transition to the specified stage if valid.

        Validates the requested transition and updates the current_stage
        if the transition is valid. Ensures that workflow stages progress
        in the correct sequence.

        Args:
            target_stage (int): The workflow stage to transition to

        Returns:
            bool: True if transition was successful, False otherwise
        """
        # Validate transition
        current = self.current_stage

        # Can always reset to initial
        if target_stage == WorkflowStages.INITIAL:
            self.current_stage = WorkflowStages.INITIAL
            return True

        # Ensure transitions are sequential
        if target_stage != current + 1 and target_stage != current:
            logger.warning(f"Invalid stage transition from {current} to {target_stage}")
            return False

        # Track the transition
        prev_stage = self.current_stage
        self.current_stage = target_stage
        logger.info(f"Transitioned from stage {prev_stage} to {target_stage}")
        return True

    def can_transition_to(self, target_stage):
        """
        Check if transition to the specified stage is valid.

        Evaluates whether a transition to the target stage is valid based
        on the current state and prerequisites for each stage.

        Args:
            target_stage (int): The workflow stage to check

        Returns:
            bool: True if the transition would be valid, False otherwise
        """
        # Can always reset to initial
        if target_stage == WorkflowStages.INITIAL:
            return True

        # Ensure transitions are sequential or to the same stage
        if (
            target_stage != self.current_stage + 1
            and target_stage != self.current_stage
        ):
            return False

        # Check stage-specific requirements
        if target_stage == WorkflowStages.CLARIFYING:
            return self.intent_parsed and self.needs_clarification

        if target_stage == WorkflowStages.CODE_GENERATION:
            return self.intent_parsed and (
                self.clarification_complete or not self.needs_clarification
            )

        if target_stage == WorkflowStages.EXECUTION:
            return self.code_generated

        if target_stage == WorkflowStages.RESULTS:
            return self.execution_complete

        return False

    def get_stage_info(self):
        """
        Get information about the current stage.

        Returns a dictionary with details about the current workflow stage,
        including its numeric ID, name, emoji, and completion status.

        Returns:
            dict: Information about the current stage
        """
        stage = self.current_stage
        return {
            "number": stage,
            "name": WorkflowStages.STAGE_NAMES.get(stage, "Unknown"),
            "emoji": WorkflowStages.STAGE_EMOJIS.get(stage, ""),
            "complete": self._is_stage_complete(stage),
        }

    def _is_stage_complete(self, stage):
        """
        Check if a specific stage is complete.

        Determines whether a given stage has been completed based on
        the current state flags.

        Args:
            stage (int): The workflow stage to check

        Returns:
            bool: True if the stage is complete, False otherwise
        """
        if stage == WorkflowStages.INITIAL:
            return self.intent_parsed

        if stage == WorkflowStages.CLARIFYING:
            return self.clarification_complete or not self.needs_clarification

        if stage == WorkflowStages.CODE_GENERATION:
            return self.code_generated

        if stage == WorkflowStages.EXECUTION:
            return self.execution_complete

        if stage == WorkflowStages.RESULTS:
            return self.results_displayed

        return False
