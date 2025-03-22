#!/bin/bash
# QByte launcher for macOS
# This script helps run QByte with automatic setup detection

# Print colorful messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}       QByte Launcher for macOS        ${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        echo -e "${YELLOW}Python command not found, but python3 is available. Using python3.${NC}"
        PYTHON_CMD="python3"
    else
        echo -e "${RED}Error: Python is not installed. Please install Python 3.6 or higher.${NC}"
        exit 1
    fi
else
    PYTHON_CMD="python"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 6 ]); then
    echo -e "${RED}Error: QByte requires Python 3.6 or higher. Found version $PYTHON_VERSION.${NC}"
    exit 1
fi

echo -e "${GREEN}Using Python $PYTHON_VERSION${NC}"

# Check if required directories exist
if [ ! -d "dataout" ]; then
    echo -e "${YELLOW}Creating dataout directory...${NC}"
    mkdir -p dataout
fi

# Check for required packages
echo -e "${BLUE}Checking required packages...${NC}"
if ! $PYTHON_CMD -c "import matplotlib, numpy, serial, scipy, astral" 2>/dev/null; then
    echo -e "${YELLOW}Some required packages are missing. Installing dependencies...${NC}"
    $PYTHON_CMD -m pip install -r requirements.txt
    
    # Check if installation was successful
    if ! $PYTHON_CMD -c "import matplotlib, numpy, serial, scipy, astral" 2>/dev/null; then
        echo -e "${RED}Error: Failed to install required packages. Please install them manually with:${NC}"
        echo -e "    pip install -r requirements.txt"
        exit 1
    fi
else
    echo -e "${GREEN}All required packages are installed.${NC}"
fi

# Check for TrueRNG devices
echo -e "${BLUE}Checking for TrueRNG devices...${NC}"
TRNG_DEVICES=$($PYTHON_CMD -c "from serial.tools import list_ports; print(len([p for p in list_ports.comports() if p[1].startswith('TrueRNG')]))")

if [ "$TRNG_DEVICES" -gt 0 ]; then
    echo -e "${GREEN}Found $TRNG_DEVICES TrueRNG device(s).${NC}"
    echo -e "${YELLOW}TrueRNG devices will be used if RandomSrc is set to 'trng' in QByte.py${NC}"
else
    echo -e "${YELLOW}No TrueRNG devices detected. Will use pseudo-random number generator.${NC}"
fi

# Get command line arguments
MODE=${1:-static}
REMARKS=${2:-_}

echo -e "${BLUE}Starting QByte with mode=$MODE, remarks=$REMARKS${NC}"
echo -e "${BLUE}========================================${NC}"

# Run QByte
$PYTHON_CMD QByte.py $MODE $REMARKS

# Check exit code
if [ $? -ne 0 ]; then
    echo -e "${RED}QByte exited with an error. Check the output above for details.${NC}"
    echo -e "${YELLOW}For troubleshooting, check 'qbyte_rng.log' for more information.${NC}"
else
    echo -e "${GREEN}QByte completed successfully.${NC}"
fi 