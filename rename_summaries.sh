#!/bin/bash
# rename_summaries.sh - Convert date-based summary files to sequential numbers

# Set terminal colors for better readability
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}========== RENAMING SUMMARY FILES ==========${NC}"
echo -e "${YELLOW}Converting from date-based to sequential numbering...${NC}\n"

# Navigate to project root directory
cd "$(dirname "$0")"

# Ensure docs directory exists
mkdir -p docs

# Get all summary files sorted by modification time (oldest first to maintain sequence)
FILES=$(find docs -name "summary_*.md" | sort -t_ -k2,2 -k3,3 -k4,4)

# Initialize counter
COUNTER=1

# Mapping file to record the changes
MAPPING_FILE="docs/summary_mapping.txt"
echo "# Original filename → New filename" > "$MAPPING_FILE"
echo "# Created $(date)" >> "$MAPPING_FILE"
echo "" >> "$MAPPING_FILE"

# Rename each file with padded numbers
for FILE in $FILES; do
    # Format counter with leading zeros
    PADDED_NUM=$(printf "%03d" $COUNTER)
    NEW_NAME="docs/summary_$PADDED_NUM.md"
    
    # Extract original date from filename for the title
    ORIGINAL_DATE=$(echo "$FILE" | grep -o '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
    
    if [ "$FILE" != "$NEW_NAME" ]; then
        echo -e "Renaming ${BLUE}$FILE${NC} to ${GREEN}$NEW_NAME${NC}"
        
        # Replace the date in the content of the file if it exists in the title
        if [ -f "$FILE" ]; then
            # Check if file has a title line
            FIRST_LINE=$(head -n 1 "$FILE")
            if [[ "$FIRST_LINE" == "# "* && "$FIRST_LINE" == *"$ORIGINAL_DATE"* ]]; then
                # Create temp file with modified content
                TMP_FILE=$(mktemp)
                
                # Replace the date in the title line with "Session #123"
                sed "1s/$ORIGINAL_DATE/Session $PADDED_NUM/" "$FILE" > "$TMP_FILE"
                
                # Move temp file to original location
                mv "$TMP_FILE" "$FILE"
                echo -e "  ${YELLOW}Updated title in $FILE${NC}"
            fi
        fi
        
        # Rename the file
        mv "$FILE" "$NEW_NAME"
        
        # Record the mapping
        echo "$FILE → $NEW_NAME" >> "$MAPPING_FILE"
    fi
    
    COUNTER=$((COUNTER+1))
done

echo -e "\n${GREEN}✓ All summary files renamed successfully!${NC}"
echo -e "Created mapping file: ${BLUE}$MAPPING_FILE${NC}\n"
echo -e "${YELLOW}Please update handoff.sh to use the new naming convention...${NC}"

# Count the total number of summary files
TOTAL_FILES=$((COUNTER-1))
echo -e "Total summary files: ${GREEN}$TOTAL_FILES${NC}"
echo -e "Next file will be: ${BLUE}docs/summary_$(printf "%03d" $COUNTER).md${NC}\n" 