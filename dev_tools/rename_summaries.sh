#!/bin/bash
# Script to rename data validation summary files to sequential numbering

# Set terminal colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========== RENAMING SUMMARY FILES ==========${NC}"
echo -e "${YELLOW}Converting from date-based to sequential numbering...${NC}\n"

# Navigate to the docs directory
cd "$(dirname "$0")/docs" || exit 1

# Function to check if a file exists
file_exists() {
    [ -f "$1" ]
}

# Add section for data validation summaries
echo "Converting data validation summaries to sequential numbering format..."

# Check if the source files exist
if file_exists "summary_data_validation_2025-05-06.md"; then
    # Ensure the destination doesn't already exist
    if ! file_exists "summary_data_validation_001.md"; then
        echo "Renaming summary_data_validation_2025-05-06.md to summary_data_validation_001.md"
        cp "summary_data_validation_2025-05-06.md" "summary_data_validation_001.md"
    else
        echo "File summary_data_validation_001.md already exists. Skipping."
    fi
fi

if file_exists "summary_data_validation_implementation_2025-05-06.md"; then
    # Ensure the destination doesn't already exist
    if ! file_exists "summary_data_validation_002.md"; then
        echo "Renaming summary_data_validation_implementation_2025-05-06.md to summary_data_validation_002.md"
        cp "summary_data_validation_implementation_2025-05-06.md" "summary_data_validation_002.md"
    else
        echo "File summary_data_validation_002.md already exists. Skipping."
    fi
fi

# Generate a simple mapping file
echo "Generating summary mapping file..."
echo "# Data Validation Summary Mapping" > validation_summary_mapping.txt
echo "This file maps sequential summary numbers to their original filenames." >> validation_summary_mapping.txt
echo "" >> validation_summary_mapping.txt
echo "- 001: summary_data_validation_2025-05-06.md (Initial Planning)" >> validation_summary_mapping.txt
echo "- 002: summary_data_validation_implementation_2025-05-06.md (Implementation Details)" >> validation_summary_mapping.txt
echo "- 003: summary_data_validation_003.md (Phase 1 Review)" >> validation_summary_mapping.txt

echo -e "\n${GREEN}✓ Data validation summary files renamed successfully!${NC}"

# Count the total number of data validation summary files
DATA_VAL_COUNT=$(ls summary_data_validation_*.md 2>/dev/null | wc -l)
NEXT_NUM=$(printf "%03d" $((DATA_VAL_COUNT + 1)))

echo -e "Total data validation summary files: ${BLUE}$DATA_VAL_COUNT${NC}"
echo -e "Next file will be: ${GREEN}summary_data_validation_$NEXT_NUM.md${NC}\n" 