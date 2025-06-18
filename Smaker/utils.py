#!/usr/bin/env python3

import re
import secrets
import string
import logging
from config import DEBUG

# Setup logger reference
logger = logging.getLogger("schedule_maker")

def generate_random_password(length=16):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def is_valid_email(email):
    """Validate email format"""
    if not email: 
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_input(text):
    """Remove potentially dangerous characters from input"""
    if not text:
        return ""
    if text == "DIEEEEE":  # Allow specific note
        return text
    # Basic sanitization - remove shell metacharacters and control codes
    # Allows common punctuation used in plan details
    # Keep pipe | for the separator, it's handled explicitly
    return re.sub(r'[;&<>$`\\\x00-\x1F\x7F]', '', text)

def debug(message):
    """Log debug messages if debug mode is on"""
    if DEBUG:
        logger.debug(f"{message}")

def clean_text(text):
    """Remove ANSI color codes and other unwanted text from string"""
    if not text:
        return ""
    text = re.sub(r'\x1B\[[0-9;]*[JKmsu]', '', text)
    text = re.sub(r'\[[0-9;]*m', '', text)
    text = re.sub(r'Study information for [^:]*:', '', text)
    text = re.sub(r'Enter specific study goals for [^(]*\(press Enter for none\):', '', text)
    text = re.sub(r'Work information for [^:]*:', '', text)  # Keep this for legacy compatibility? Maybe remove.
    text = re.sub(r'Add another plan for .* \(y/n\):', '', text)  # Clean up new prompt
    text = re.sub(r'Plan Name:', '', text)
    text = re.sub(r'Plan Details \(e\.g\., hours, location\):', '', text)
    return text.strip()