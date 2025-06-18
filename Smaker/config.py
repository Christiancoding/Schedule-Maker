from pathlib import Path
from datetime import datetime
import os
import sys
import logging
import tkinter as tk
import configparser
# =============================================================================
# == Configuration Module for Schedule Maker ==
# =============================================================================
# This module defines paths, constants, and default settings for the schedule maker.

#!/usr/bin/env python3

import os
from pathlib import Path
from datetime import datetime

# --- Define paths using Path for platform independence and security ---
HOME = Path.home()
CONFIG_DIR = HOME / ".schedule_config"
SCHEDULE_DIR = HOME / ".schedule_config/Schedules"
ANSWERS_DIR = HOME / ".schedule_config/PA"
SCHEDULE_FILE = SCHEDULE_DIR / "schedule.txt"
REMINDERS_FILE = SCHEDULE_DIR / "schedule_reminders.txt"
ANSWERS_FILE = ANSWERS_DIR / "previous_answers.sh"
NOTES_FILE = CONFIG_DIR / "schedule_notes.txt"
CONFIG_FILE = CONFIG_DIR / "config.sh"  # Legacy config file (read-only)
CREDENTIALS_FILE = CONFIG_DIR / "credentials.ini"
HTML_FILE = CONFIG_DIR / "schedule_email.html"
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# --- Default email settings - will be overridden by config ---
DEFAULT_EMAIL = "your_default_recipient@example.com"

# --- Days of the week ---
DAYS = ["Monday", "Tues", "Wed", "Thur", "Fri", "Sat", "Sun"]

# --- Default study times by day ---
DEFAULT_STUDY_TIMES = {
    "Monday": "11:00-3:00", 
    "Tues": "11:00-3:00", 
    "Wed": "11:00-3:00",
    "Thur": "11:00-3:00", 
    "Fri": "11:00-3:00", 
    "Sat": "11:00-3:00",
    "Sun": "12:00-2:00"
}

# --- ANSI color codes for terminal output (CLI only) ---
class Color:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    NC = '\033[0m'  # No Color

# --- Debug mode (True=on, False=off) ---
DEBUG = False

# --- Keyring Service Name ---
KEYRING_SERVICE = "schedule_maker_email"

# --- Constants ---
PLAN_SAVE_SEPARATOR = "||PLANS||"  # Unique separator for plans JSON in save file

# --- Ensure directories exist ---
def ensure_directories():
    """Create necessary directories if they don't exist."""
    CONFIG_DIR.mkdir(exist_ok=True, parents=True)
    SCHEDULE_DIR.mkdir(exist_ok=True, parents=True)
    ANSWERS_DIR.mkdir(exist_ok=True, parents=True)

# Call this when the module is imported
ensure_directories()
# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create and export logger
logger = logging.getLogger("schedule_maker")