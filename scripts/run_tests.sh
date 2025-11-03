#!/bin/bash

# Stock Lambda Consumer - Test Runner Script
# Runs the complete test suite

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stock Lambda Consumer - Test Suite${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q -r requirements.txt
pip install -q -r test_requirements.txt

# Run tests
echo ""
echo -e "${GREEN}Running tests...${NC}"
echo ""

# Run with coverage
pytest tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    "$@"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Tests failed!${NC}"
    echo -e "${RED}========================================${NC}"
fi

deactivate
exit $TEST_EXIT_CODE
