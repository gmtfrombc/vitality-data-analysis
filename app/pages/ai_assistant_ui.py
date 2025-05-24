"""
Panel UI construction for the AI Assistant page.

This module contains all Panel layout, widget, and component construction for the AI Assistant.
Business logic and state management remain in ai_assistant.py.
"""

import panel as pn
import logging
from app.state import WorkflowStages

# If needed, import other UI dependencies (e.g., pn.widgets, pn.pane, etc.)

print("ai_assistant_ui module imported")


def build_assistant_view(ai_assistant):
    """
    Build the Panel UI for the AI Assistant, using the provided ai_assistant instance for state and callbacks.

    Args:
        ai_assistant: An instance of AIAssistant (from ai_assistant.py)

    Returns:
        A Panel layout (pn.Column or pn.Row) representing the full assistant UI.
    """
    print("[DEBUG] build_assistant_view called")
    logger = logging.getLogger("ai_assistant_ui")

    # Create title and description
    title = pn.pane.Markdown("# AI SQL Assistant", sizing_mode="stretch_width")
    description = pn.pane.Markdown(
        """
        Ask questions about the patient data in natural language, and the AI will 
        generate SQL queries to answer your questions.
        
        **Examples:**
        - "Show me all female patients with an engagement score above 80"
        - "Find patients over 50 with vitality scores below 20"
        - "List patients who started with high blood pressure but improved in their latest reading"
        - "What's the average BMI change for patients with heart_fit_score above 70?"
        """
    )

    # Watch for status changes
    def update_status(event):
        if ai_assistant.ui:
            ai_assistant.ui.update_status(event.new, type="info")

    ai_assistant.param.watch(update_status, "status_message")

    # Create query input
    query_input = pn.widgets.TextAreaInput(
        name="Your Question",
        placeholder="Enter your question here...",
        value=ai_assistant.query_text,
        height=100,
        sizing_mode="stretch_width",
    )
    query_input.link(ai_assistant, value="query_text")

    # Create generate button
    generate_button = pn.widgets.Button(
        name="Generate SQL",
        button_type="primary",
        width=150,
        disabled=not bool(ai_assistant.api_key),
    )
    generate_button.on_click(ai_assistant.generate_sql)

    # Create SQL display
    sql_display = pn.widgets.TextAreaInput(
        name="Generated SQL",
        value=ai_assistant.generated_sql,
        height=150,
        sizing_mode="stretch_width",
    )
    ai_assistant.param.watch(
        lambda event: setattr(sql_display, "value", event.new), "generated_sql"
    )

    # Create validation status badge
    validation_badge = pn.pane.HTML(
        "<span class='validation-badge' style='display:none;'></span>",
        width=100,
        height=30,
        margin=(5, 0, 0, 10),
    )

    # Create validate and execute buttons
    validate_button = pn.widgets.Button(
        name="Validate SQL", button_type="primary", width=150, disabled=True
    )
    execute_button = pn.widgets.Button(
        name="Execute Query", button_type="success", width=150, disabled=True
    )

    # Create a dynamic results component
    results_container = pn.Column(
        pn.pane.Markdown("No results to display. Generate and execute a query."),
        sizing_mode="stretch_width",
    )
    ai_assistant.results_container = results_container

    # For reset functionality
    reset_references = {"query_input": query_input}
    reset_button = pn.widgets.Button(name="Reset Form", button_type="danger", width=150)
    reset_button.on_click(
        lambda event: ai_assistant._reset(event, reset_references, results_container)
    )

    # Enable buttons only when SQL is generated
    def update_buttons(event):
        validate_button.disabled = not bool(event.new)
        execute_button.disabled = not bool(event.new)
        validation_badge.object = (
            "<span class='validation-badge' style='display:none;'></span>"
        )

    ai_assistant.param.watch(update_buttons, "generated_sql")

    validate_button.on_click(
        lambda event: ai_assistant._validate_button_click(event, validation_badge)
    )
    execute_button.on_click(lambda event: ai_assistant._execute_sql(event))

    # Create save query components
    query_name_input = pn.widgets.TextInput(
        name="Query Name",
        placeholder="Enter a name for this query...",
        value=ai_assistant.query_name,
        width=300,
    )
    query_name_input.link(ai_assistant, value="query_name")
    save_query_button = pn.widgets.Button(
        name="Save Query",
        button_type="primary",
        width=100,
        disabled=not bool(ai_assistant.api_key),
    )
    save_query_button.on_click(ai_assistant._save_query)

    # Create saved queries panel
    saved_queries_title = pn.pane.Markdown("## Saved Queries")
    print(f"[build_assistant_view] Initial saved_queries: {ai_assistant.saved_queries}")
    saved_queries_list = pn.widgets.Select(
        name="Saved Queries",
        options={q["name"]: i for i, q in enumerate(ai_assistant.saved_queries)},
        size=10,
        width=250,
    )
    load_query_button = pn.widgets.Button(
        name="Load",
        button_type="default",
        width=100,
        disabled=len(ai_assistant.saved_queries) == 0,
    )
    delete_query_button = pn.widgets.Button(
        name="Delete",
        button_type="danger",
        width=100,
        disabled=len(ai_assistant.saved_queries) == 0,
    )

    def load_query(event):
        if (
            saved_queries_list.value is not None
            and 0 <= saved_queries_list.value < len(ai_assistant.saved_queries)
        ):
            selected_query = ai_assistant.saved_queries[saved_queries_list.value]
            ai_assistant.query_text = selected_query["query"]
            ai_assistant.query_name = selected_query["name"]
            ai_assistant.status_message = f"Loaded query: {selected_query['name']}"

    def delete_query(event):
        if (
            saved_queries_list.value is not None
            and 0 <= saved_queries_list.value < len(ai_assistant.saved_queries)
        ):
            deleted_name = ai_assistant.saved_queries[saved_queries_list.value]["name"]
            del ai_assistant.saved_queries[saved_queries_list.value]
            ai_assistant._save_queries_to_file()
            saved_queries_list.options = {
                q["name"]: i for i, q in enumerate(ai_assistant.saved_queries)
            }
            load_query_button.disabled = len(ai_assistant.saved_queries) == 0
            delete_query_button.disabled = len(ai_assistant.saved_queries) == 0
            ai_assistant.status_message = f"Deleted query: {deleted_name}"

    load_query_button.on_click(load_query)
    delete_query_button.on_click(delete_query)

    def update_saved_queries_list(event):
        print(f"[update_saved_queries_list] New value: {event.new}")
        saved_queries_list.options = {q["name"]: i for i, q in enumerate(event.new)}
        load_query_button.disabled = len(event.new) == 0
        delete_query_button.disabled = len(event.new) == 0

    ai_assistant.param.watch(update_saved_queries_list, "saved_queries")

    env_info = pn.pane.Markdown(
        """
        **Note:** This AI Assistant requires the OPENAI_API_KEY environment variable to be set.
        
        To set the environment variable:
        
        On macOS/Linux:
        ```
        export OPENAI_API_KEY="your_api_key_here"
        ```
        
        On Windows:
        ```
        set OPENAI_API_KEY=your_api_key_here
        ```
        
        For more detailed logging during development, set DEBUG=true:
        ```
        export DEBUG=true  # For macOS/Linux
        set DEBUG=true     # For Windows
        ```
        
        Then restart the application.
        """,
        styles={"background": "#f8f9fa", "padding": "10px", "border-radius": "5px"},
    )
    api_key_info = env_info if not ai_assistant.api_key else pn.pane.Markdown("")

    sql_header = pn.Row(
        pn.pane.Markdown("### Step 2: Review the SQL", margin=(0, 0, 10, 0)),
        validation_badge,
        sizing_mode="stretch_width",
    )
    button_row = pn.Row(
        pn.Row(generate_button, validate_button, execute_button, width=500),
        pn.layout.HSpacer(),
        reset_button,
        sizing_mode="stretch_width",
    )
    save_row = pn.Row(query_name_input, save_query_button)
    query_buttons_row = pn.Row(load_query_button, delete_query_button)
    schema_accordion = pn.Accordion(
        ("Database Schema", pn.pane.Markdown(ai_assistant.db_schema)), toggle=True
    )

    # --- Import/Mock Data Handling UI ---
    import_status = pn.pane.Markdown(
        "", sizing_mode="stretch_width", styles={"color": "#333"}
    )
    import_file_input = pn.widgets.FileInput(accept=".json")
    import_button = pn.widgets.Button(
        name="Import JSON", button_type="primary", width=120, disabled=True
    )
    import_spinner = pn.indicators.LoadingSpinner(
        value=True, visible=False, width=30, height=30, color="primary"
    )
    reset_mock_button = pn.widgets.Button(
        name="Reset Mock Patients", button_type="danger", width=180
    )

    def set_import_status(msg, type_):
        color = {
            "info": "#333",
            "success": "green",
            "error": "red",
            "warning": "orange",
        }.get(type_, "#333")
        import_status.object = f"<span style='color:{color}'>{msg}</span>"
        print(f"[Import/Reset Status] {msg}")
        logger.info(f"[Import/Reset Status] {msg}")

    def on_file_change(event):
        import_button.disabled = not bool(event.new)

    import_file_input.param.watch(on_file_change, "value")

    def on_import_click(event):
        if not import_file_input.value:
            set_import_status("No file selected.", "warning")
            return
        import_button.disabled = True
        import_file_input.disabled = True
        import_spinner.visible = True
        set_import_status("Uploading file...", "info")

        def status_callback(msg, type_):
            set_import_status(msg, type_)
            if type_ in ("success", "error"):
                import_button.disabled = False
                import_file_input.disabled = False
                import_spinner.visible = False

        ai_assistant.import_json_data(import_file_input.value, status_callback)

    import_button.on_click(on_import_click)

    def on_reset_mock_click(event):
        reset_mock_button.disabled = True
        set_import_status("Resetting mock/demo patients...", "info")

        def status_callback(msg, type_):
            set_import_status(msg, type_)
            if type_ in ("success", "error"):
                reset_mock_button.disabled = False

        ai_assistant.reset_mock_patients(status_callback)

    reset_mock_button.on_click(on_reset_mock_click)

    import_panel = pn.Column(
        pn.pane.Markdown("### Data Import & Mock Reset", margin=(0, 0, 5, 0)),
        pn.Row(import_file_input, import_spinner, align="center"),
        import_button,
        reset_mock_button,
        import_status,
        sizing_mode="stretch_width",
        styles={
            "background": "#f8f9fa",
            "border-radius": "5px",
            "margin-bottom": "10px",
        },
        css_classes=["card", "rounded-card"],
    )

    # --- Top Title (smaller, left-aligned, with padding) ---
    top_title = pn.pane.Markdown(
        """
        <div style='padding-top:18px; padding-bottom:12px; padding-left:8px; text-align:left;'>
            <span style='font-size:1.6rem; font-weight:600; letter-spacing:0.01em;'>AI Data Analysis</span>
        </div>
        """,
        sizing_mode="stretch_width",
        margin=(0, 0, 0, 0),
    )

    # --- Left Sidebar: Title + Saved Questions + Import/Reset ---
    left_sidebar = pn.Column(
        top_title,
        saved_queries_title,
        saved_queries_list,
        query_buttons_row,
        pn.layout.Divider(),
        import_panel,
        width=340,  # 1/4 of a ~1400px screen
        min_width=300,
        max_width=400,
        margin=0,
        scroll=True,
        styles={"z-index": "1000"},
    )

    # --- Workflow Progress Indicator ---
    stage_names = [
        WorkflowStages.STAGE_NAMES[i]
        for i in range(WorkflowStages.INITIAL, WorkflowStages.RESULTS + 1)
    ]
    stage_emojis = [
        WorkflowStages.STAGE_EMOJIS[i]
        for i in range(WorkflowStages.INITIAL, WorkflowStages.RESULTS + 1)
    ]

    def get_stage_indicator(current_stage):
        items = []
        for i, (name, emoji) in enumerate(zip(stage_names, stage_emojis)):
            if i < current_stage:
                color = "#4caf50"  # completed: green
            elif i == current_stage:
                color = "#2196f3"  # active: blue
            else:
                color = "#bdbdbd"  # pending: gray
            items.append(
                pn.pane.HTML(
                    f"<div style='margin-bottom:12px;'>"
                    f"<span style='font-size:1.5em;'>{emoji}</span> "
                    f"<span style='color:{color};font-weight:bold;margin-left:8px'>{name}</span>"
                    f"</div>"
                )
            )
        return pn.Column(*items, sizing_mode="stretch_width")

    workflow_stage_indicator = pn.bind(
        get_stage_indicator, ai_assistant.workflow_state.param.current_stage
    )

    continue_button = pn.widgets.Button(
        name="Continue",
        button_type="primary",
        width=150,
        align="center",
    )
    continue_button.on_click(lambda event: ai_assistant.continue_workflow())

    # --- End Workflow Progress Indicator ---

    # --- Clarification Panel ---
    clarification_panel = pn.Column()
    clarification_input = pn.widgets.TextAreaInput(
        name="Clarification",
        placeholder="Please clarify your request...",
        height=80,
        sizing_mode="stretch_width",
        visible=False,
    )
    submit_clarification_button = pn.widgets.Button(
        name="Submit Clarification",
        button_type="success",
        width=200,
        visible=False,
    )

    def update_clarification_panel():
        stage = ai_assistant.workflow_state.current_stage
        if stage == WorkflowStages.CLARIFYING:
            print("[UI] Displaying clarification panel.")
            logger.info("Displaying clarification panel.")
            clarification_panel.objects = []
            questions = ai_assistant.clarifying_questions or [
                "Please clarify your request."
            ]
            clarification_panel.append(
                pn.pane.Markdown(
                    "\n".join([f"**Q{i+1}:** {q}" for i, q in enumerate(questions)])
                )
            )
            clarification_input.value = ""
            clarification_input.visible = True
            submit_clarification_button.visible = True
            clarification_panel.append(clarification_input)
            clarification_panel.append(submit_clarification_button)
        else:
            clarification_panel.objects = []
            clarification_input.visible = False
            submit_clarification_button.visible = False

    def on_submit_clarification(event):
        response = clarification_input.value.strip()
        if response:
            ai_assistant.submit_clarification(response)
            update_clarification_panel()  # Hide panel after submit
            # Advance workflow to next stage
            ai_assistant.continue_workflow()
        else:
            print("[UI] Clarification response is empty.")
            logger.info("Clarification response is empty.")

    submit_clarification_button.on_click(on_submit_clarification)
    ai_assistant.workflow_state.param.watch(
        lambda event: update_clarification_panel(), "current_stage"
    )
    # --- End Clarification Panel ---

    # --- Analyze Button ---
    analyze_button = pn.widgets.Button(
        name="Analyze",
        button_type="primary",
        width=150,
        align="center",
        disabled=not bool(query_input.value.strip()),
    )

    def on_analyze_click(event):
        print(f"[UI] Analyze button pressed. Query: {query_input.value}")
        logger.info(f"Analyze button pressed. Query: {query_input.value}")
        ai_assistant.start_workflow(query_input.value)

    analyze_button.on_click(on_analyze_click)

    def update_analyze_button(event):
        analyze_button.disabled = not bool(event.new.strip())

    query_input.param.watch(update_analyze_button, "value")
    # --- End Analyze Button ---

    # --- Feedback Widget ---
    persistent_feedback_widget = FeedbackWidget(query=ai_assistant.query_text)
    feedback_panel = pn.Column(
        persistent_feedback_widget.view(), sizing_mode="stretch_width"
    )

    def update_feedback_panel():
        print(
            f"[DEBUG] update_feedback_panel called. Query: '{ai_assistant.query_text}'"
        )
        persistent_feedback_widget.query = ai_assistant.query_text
        persistent_feedback_widget.comment = ""
        persistent_feedback_widget.rating = ""
        persistent_feedback_widget.submitted = False
        persistent_feedback_widget.thumbs_up.visible = True
        persistent_feedback_widget.thumbs_down.visible = True
        persistent_feedback_widget.comment_input.visible = True
        persistent_feedback_widget.submit_button.visible = True
        persistent_feedback_widget.thank_you.visible = False
        feedback_panel.visible = bool(ai_assistant.query_text.strip())
        print(f"[DEBUG] feedback_panel.visible: {feedback_panel.visible}")

    print("[DEBUG] Registering workflow_state watcher for update_feedback_panel")
    ai_assistant.workflow_state.param.watch(
        lambda event: (
            print("[DEBUG] workflow_state watcher fired"),
            update_feedback_panel(),
        ),
        "current_stage",
    )
    print("[DEBUG] Registering query_text watcher for update_feedback_panel")
    ai_assistant.param.watch(
        lambda event: (
            print("[DEBUG] query_text watcher fired"),
            update_feedback_panel(),
        ),
        "query_text",
    )
    # --- End Feedback Widget ---

    main_content = pn.Column(
        title,
        description,
        pn.layout.Divider(),
        api_key_info,
        pn.layout.Divider(),
        pn.pane.Markdown("### Step 1: Ask your question"),
        query_input,
        analyze_button,
        clarification_panel,
        pn.layout.Divider(),
        pn.pane.Markdown("## Workflow Progress"),
        workflow_stage_indicator,
        continue_button,
        pn.layout.Divider(),
        sql_header,
        sql_display,
        button_row,
        pn.layout.Divider(),
        pn.pane.Markdown("### Step 3: View Results"),
        results_container,
        feedback_panel,
        pn.layout.Divider(),
        pn.pane.Markdown("### Save This Query"),
        save_row,
        pn.layout.Divider(),
        schema_accordion,
        min_width=800,
        sizing_mode="stretch_width",
    )

    # --- Main Content (AI SQL Assistant) ---
    main_content.sizing_mode = "stretch_both"
    main_content.min_width = 900  # 3/4 of a ~1400px screen
    main_content.max_width = 1200

    # --- Layout: Side-by-side (Row) with width ratios ---
    layout = pn.Row(
        left_sidebar,
        pn.layout.HSpacer(width=20),
        main_content,
        sizing_mode="stretch_both",
        margin=0,
        width_policy="max",
        height_policy="max",
    )
    update_feedback_panel()  # Force feedback widget to initialize after UI build
    return layout
