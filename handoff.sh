#!/bin/bash
# handoff.sh - Assistant Transition & Documentation Update Script
# Run this script when you're ready to end a session with one assistant and prepare for the next.

# Set terminal colors for better readability
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}========== ASSISTANT HANDOFF PROCESS ==========${NC}"
echo -e "${YELLOW}Running pre-handoff checks and documentation updates...${NC}\n"

# Navigate to project root directory
cd "$(dirname "$0")"

# Step 1: Run the self-test to ensure everything is working
echo -e "${BLUE}STEP 1: Running synthetic self-test to validate assistant functionality...${NC}"
./run_self_test.sh
TEST_EXIT_CODE=$?

# Show test results and set status
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✓ Self-test completed successfully!${NC}\n"
    TEST_STATUS="PASSED"
else
    echo -e "\n${RED}✗ Self-test failed. Please fix issues before handing off.${NC}\n"
    TEST_STATUS="FAILED"
fi

# Step 2: Generate a checklist for documentation updates
TODAY_DATE=$(date +"%Y-%m-%d")
LAST_SUMMARY=$(ls -t docs/summary_* 2>/dev/null | head -1 || echo "No previous summary found")

echo -e "${BLUE}STEP 2: Documentation update checklist${NC}"
echo -e "Please ensure these documents are updated before handoff:\n"
echo -e "1. ${YELLOW}CHANGELOG.md${NC} - Add entries for all new features, fixes, and changes"
echo -e "2. ${YELLOW}ROADMAP_CANVAS.md${NC} - Update status of completed items and current priorities"
echo -e "3. ${YELLOW}docs/summary_${TODAY_DATE}.md${NC} - Create or update today's summary (previous: ${LAST_SUMMARY})"

# Generate documentation template if needed
if [ ! -f "docs/summary_${TODAY_DATE}.md" ]; then
    echo -e "\n${BLUE}Creating new summary template for today...${NC}"
    mkdir -p docs
    
    cat > "docs/summary_${TODAY_DATE}.md" <<-EOF
# Metabolic Health Program - Development Summary (${TODAY_DATE})

## Overview
[Brief description of today's progress and key achievements]

## Completed Tasks
- [List major completed tasks]

## Current Status
- Self-test status: ${TEST_STATUS}
- [Other relevant status information]

## Next Steps
- [List of upcoming tasks or priorities]

## Technical Notes
- [Any implementation details worth noting]
EOF

    echo -e "${GREEN}✓ Created new summary template: docs/summary_${TODAY_DATE}.md${NC}\n"
fi

# Step 3: Generate the handoff message for the assistant
echo -e "${BLUE}STEP 3: Assistant handoff message${NC}\n"
echo -e "${GREEN}=== COPY THIS MESSAGE FOR THE ASSISTANT ===${NC}"
echo "
It's time to close this session. Please perform the following handoff tasks:

1. UPDATE DOCUMENTATION:
   - Review and update CHANGELOG.md with new entries
   - Update ROADMAP_CANVAS.md to reflect current progress (mark items as complete/in-progress)
   - Complete today's summary in docs/summary_${TODAY_DATE}.md

2. VALIDATION:
   - Self-test status: ${TEST_STATUS}
   - Please address any failing tests or add notes about known issues

3. VERSION CONTROL:
   - Stage all documentation changes
   - Commit with message: \"docs: update summary and progress for ${TODAY_DATE}\"
   - Push changes to the repository if applicable

Once these tasks are complete, the project will be ready for the next assistant session.
"
echo -e "${GREEN}=========================================${NC}\n"

# Step 4: Provide guidance for the user
echo -e "${BLUE}NEXT STEPS:${NC}"
echo -e "1. Confirm that the assistant has completed the documentation updates"
echo -e "2. After the handoff is complete, start a new session with the next assistant"
echo -e "3. Run 'git log' to confirm that the documentation changes were committed\n"

# Show documentation status
echo -e "${BLUE}DOCUMENTATION STATUS:${NC}"
echo -e "CHANGELOG.md: $(git diff --name-only CHANGELOG.md | grep -q CHANGELOG.md && echo "Modified" || echo "Unchanged")"
echo -e "ROADMAP_CANVAS.md: $(git diff --name-only ROADMAP_CANVAS.md | grep -q ROADMAP_CANVAS.md && echo "Modified" || echo "Unchanged")"
echo -e "Today's summary: $(git ls-files --error-unmatch docs/summary_${TODAY_DATE}.md 2>/dev/null && echo "Created" || echo "Not yet added to git")\n"

echo -e "${GREEN}Handoff script completed.${NC}" 