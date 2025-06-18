#!/usr/bin/env python3

import os
import re
import smtplib
import shutil
import json
import subprocess
import time
import getpass
import configparser
import keyring
import keyring.errors
import html as html_escaper
import css_inline
import textwrap
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font as tkFont
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from pathlib import Path
import logging

# Import from our config and utils modules
from config import *
from utils import *

# Get logger
logger = logging.getLogger("schedule_maker")

class ScheduleManager:
    """Handles loading, saving, generating, and managing schedule data."""

    def __init__(self):
        self.schedule = self.initialize_default_schedule()
        self.credentials = {'email_to': DEFAULT_EMAIL, 'email_from': '', 'smtp_server': '', 'smtp_port': 587, 'smtp_user': '', 'smtp_pass': None}
        self.additional_notes = ""
        self.load_legacy_config()
        self.load_credentials()
        self.load_schedule_data() # Load potentially new format
        self.load_notes()

    def initialize_default_schedule(self):
        """Create default schedule data structure with plans list"""
        schedule = {}
        for day in DAYS:
            schedule[day] = {
                "study_time": DEFAULT_STUDY_TIMES.get(day, "11:00-3:00"),
                "goals": "",
                "plans": [] # Initialize with an empty list for plans
                # Removed: dg_work, dg_hours, jj_work, jj_hours, notes
            }
        return schedule

    def load_legacy_config(self):
        """Load configuration from legacy config.sh (read-only)"""
        global DEFAULT_EMAIL
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: # Specify encoding
                    content = f.read()
                    email_match = re.search(r'EMAIL="([^"]*)"', content)
                    if email_match:
                        loaded_email = email_match.group(1)
                        if self.credentials['email_to'] == DEFAULT_EMAIL:
                             self.credentials['email_to'] = loaded_email
                             debug(f"Loaded legacy config: Recipient Email={loaded_email}")
                        else:
                             debug(f"Legacy config found, but recipient email already set to {self.credentials['email_to']}. Ignoring legacy email.")
            except Exception as e:
                 logger.warning(f"Could not read legacy config file {CONFIG_FILE}: {e}")

    def load_credentials(self, prompt_if_missing=False, parent_widget=None):
        """Load email credentials from config file and secure keyring storage."""
        config = configparser.ConfigParser()
        if CREDENTIALS_FILE.exists():
            try:
                config.read(CREDENTIALS_FILE)
                if 'Email' in config:
                    self.credentials['email_to'] = config['Email'].get('email_to', self.credentials.get('email_to', DEFAULT_EMAIL))
                    self.credentials['email_from'] = config['Email'].get('email_from', '')
                    self.credentials['smtp_server'] = config['Email'].get('smtp_server', 'smtp.gmail.com')
                    self.credentials['smtp_port'] = config['Email'].getint('smtp_port', 587)
                    self.credentials['smtp_user'] = config['Email'].get('smtp_user', self.credentials.get('email_from', ''))
                    debug("Non-sensitive credentials loaded from file.")
            except (configparser.Error, ValueError, KeyError) as e:
                 logger.error(f"Error reading credentials file {CREDENTIALS_FILE}: {e}. Using defaults/prompting.")
                 self.credentials['email_to'] = self.credentials.get('email_to', DEFAULT_EMAIL)
                 self.credentials['email_from'] = ''
                 self.credentials['smtp_server'] = 'smtp.gmail.com'
                 self.credentials['smtp_port'] = 587
                 self.credentials['smtp_user'] = ''

        password_found_in_keyring = False
        if self.credentials.get('smtp_user'):
            try:
                password = keyring.get_password(KEYRING_SERVICE, self.credentials['smtp_user'])
                if password:
                    # Don't store password in self.credentials, just check if it exists
                    password_found_in_keyring = True
                    debug(f"Password found in keyring for user {self.credentials['smtp_user']}.")
                else:
                    self.credentials['smtp_pass'] = None # Ensure it's None if not found (though we don't store it anyway)
                    debug(f"Password not found in keyring for user {self.credentials['smtp_user']}.")
            except keyring.errors.NoKeyringError:
                logger.warning("Keyring backend not found. Password cannot be securely stored or retrieved.")
                self.credentials['smtp_pass'] = None
            except Exception as e:
                logger.error(f"Error accessing keyring: {e}")
                self.credentials['smtp_pass'] = None

        should_prompt = prompt_if_missing and (
            not self.credentials.get('email_from') or
            not self.credentials.get('smtp_user') or
            not self.credentials.get('smtp_server') or
            not password_found_in_keyring
        )

        if should_prompt:
            logger.info("Credentials incomplete or password missing. Prompting user.")
            if parent_widget:
                self._prompt_credentials_gui(parent_widget)
            else:
                self._prompt_credentials_cli()
        elif not password_found_in_keyring and self.credentials.get('email_from') and self.credentials.get('smtp_user'):
             logger.warning(f"Password for {self.credentials['smtp_user']} not found in keyring. Email sending may fail.")

        # Ensure in-memory password is None after loading/prompting
        self.credentials['smtp_pass'] = None

        return self.credentials

    def _prompt_credentials_cli(self):
        """Prompt for credentials using the command line and save to keyring."""
        from cli_interface import print_header, ask_yes_no  # Import here to avoid circular import
        
        print_header("EMAIL CONFIGURATION (CLI)")
        print("Enter/Update email settings. Password stored securely in system keyring.")

        current_email_to = self.credentials.get('email_to', DEFAULT_EMAIL)
        email_to = input(f"Recipient email [{current_email_to}]: ").strip() or current_email_to
        while not is_valid_email(email_to):
            print(f"{Color.RED}Invalid email format. Please try again.{Color.NC}")
            email_to = input(f"Recipient email [{current_email_to}]: ").strip() or current_email_to
        self.credentials['email_to'] = email_to

        current_email_from = self.credentials.get('email_from', '')
        email_from = input(f"Sender email [{current_email_from}]: ").strip() or current_email_from
        while not is_valid_email(email_from):
            print(f"{Color.RED}Invalid email format. Please try again.{Color.NC}")
            email_from = input("Sender email: ").strip()
        self.credentials['email_from'] = email_from

        if not email_from:
            print(f"{Color.YELLOW}Sender email not provided. Skipping SMTP setup. Notifications will not work.{Color.NC}")
            self.credentials.update({'smtp_server': '', 'smtp_port': 587, 'smtp_user': '', 'smtp_pass': None})
            self.save_credentials()
            return

        current_smtp_server = self.credentials.get('smtp_server', 'smtp.gmail.com')
        self.credentials['smtp_server'] = input(f"SMTP server [{current_smtp_server}]: ").strip() or current_smtp_server

        current_smtp_port = self.credentials.get('smtp_port', 587)
        smtp_port_str = input(f"SMTP port [{current_smtp_port}]: ").strip() or str(current_smtp_port)
        try:
            self.credentials['smtp_port'] = int(smtp_port_str)
        except ValueError:
            print(f"{Color.YELLOW}Invalid port number. Using default {current_smtp_port}.{Color.NC}")
            self.credentials['smtp_port'] = current_smtp_port

        current_smtp_user = self.credentials.get('smtp_user', '')
        default_user_prompt = current_smtp_user if current_smtp_user else email_from
        self.credentials['smtp_user'] = input(f"SMTP username [{default_user_prompt}]: ").strip() or default_user_prompt

        # --- Get password and save to keyring ---
        # Check if password exists in keyring for the *current* user
        password_exists_for_user = False
        try:
            if keyring.get_password(KEYRING_SERVICE, self.credentials['smtp_user']):
                 password_exists_for_user = True
        except Exception:
             pass # Ignore keyring errors here, handled below

        ask_for_password = True
        if password_exists_for_user:
             if ask_yes_no(f"Password already stored for {self.credentials['smtp_user']}. Update it?", default="no"):
                  ask_for_password = True
             else:
                  ask_for_password = False

        if ask_for_password:
            print(f"Enter SMTP password for {self.credentials['smtp_user']} (leave blank to keep existing if unchanged, or clear):")
            password = getpass.getpass()
            if password:
                try:
                    keyring.set_password(KEYRING_SERVICE, self.credentials['smtp_user'], password)
                    # Don't store in self.credentials['smtp_pass']
                    print(f"{Color.GREEN}Password securely stored/updated in keyring for user {self.credentials['smtp_user']}.{Color.NC}")
                except keyring.errors.NoKeyringError:
                     logger.error("Keyring backend not found. Password cannot be securely stored.")
                     print(f"{Color.RED}ERROR: No system keyring found. Password cannot be saved securely.{Color.NC}")
                except Exception as e:
                     logger.error(f"Error saving password to keyring: {e}")
                     print(f"{Color.RED}ERROR: Could not save password to keyring: {e}{Color.NC}")
            elif password_exists_for_user:
                 print(f"{Color.YELLOW}Password unchanged for {self.credentials['smtp_user']}.{Color.NC}")
            else:
                print(f"{Color.YELLOW}No password entered or stored. Email sending will require password entry if not configured elsewhere.{Color.NC}")
                # Attempt to delete old password from keyring if username changed
                if self.credentials['smtp_user'] != current_smtp_user and current_smtp_user:
                    try:
                        keyring.delete_password(KEYRING_SERVICE, current_smtp_user)
                        logger.info(f"Deleted old password for user {current_smtp_user} from keyring.")
                    except (keyring.errors.PasswordDeleteError, keyring.errors.NoKeyringError):
                        logger.warning(f"Could not delete old password for {current_smtp_user} from keyring.")
                    except Exception as e:
                        logger.warning(f"Error deleting old password for {current_smtp_user} from keyring: {e}")

        self.save_credentials()
        print(f"{Color.GREEN}Non-sensitive credentials saved.{Color.NC}")

    def _prompt_credentials_gui(self, parent):
        """Prompt for credentials using a Tkinter dialog and save to keyring."""
        dialog = tk.Toplevel(parent)
        dialog.title("Email Configuration")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg='#f0f0f0')
        style = ttk.Style(dialog)
        style.configure("TLabel", background='#f0f0f0')
        style.configure("TEntry", fieldbackground='white')
        style.configure("TButton", padding=5)

        frame = ttk.Frame(dialog, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Email Setup", font=tkFont.Font(weight='bold')).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Configure settings. Password stored in system keyring.").grid(row=1, column=0, columnspan=2, pady=(0, 10))

        email_to_var = tk.StringVar(value=self.credentials.get('email_to', DEFAULT_EMAIL))
        email_from_var = tk.StringVar(value=self.credentials.get('email_from', ''))
        smtp_server_var = tk.StringVar(value=self.credentials.get('smtp_server', 'smtp.gmail.com'))
        smtp_port_var = tk.StringVar(value=str(self.credentials.get('smtp_port', 587)))
        default_smtp_user = self.credentials.get('smtp_user', self.credentials.get('email_from', ''))
        smtp_user_var = tk.StringVar(value=default_smtp_user)
        smtp_pass_var = tk.StringVar()

        def update_smtp_user(*args):
            sender_email = email_from_var.get().strip()
            current_user = smtp_user_var.get().strip()
            if not current_user and sender_email:
                 smtp_user_var.set(sender_email)
        email_from_var.trace_add("write", update_smtp_user)

        ttk.Label(frame, text="Recipient Email:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=email_to_var, width=40).grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(frame, text="Sender Email:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        sender_entry = ttk.Entry(frame, textvariable=email_from_var, width=40)
        sender_entry.grid(row=3, column=1, padx=5, pady=5)
        ttk.Label(frame, text="SMTP Server:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=smtp_server_var, width=40).grid(row=4, column=1, padx=5, pady=5)
        ttk.Label(frame, text="SMTP Port:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=smtp_port_var, width=10).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="SMTP Username:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=smtp_user_var, width=40).grid(row=6, column=1, padx=5, pady=5)
        ttk.Label(frame, text="SMTP Password:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=smtp_pass_var, show="*", width=40).grid(row=7, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(Leave blank to keep existing password)", font=tkFont.Font(slant='italic')).grid(row=8, column=1, sticky=tk.W, padx=5)

        status_label = ttk.Label(frame, text="", foreground="red")
        status_label.grid(row=9, column=0, columnspan=2, pady=5)

        def save_and_close():
            email_to = email_to_var.get().strip()
            email_from = email_from_var.get().strip()
            smtp_server = smtp_server_var.get().strip()
            smtp_port_str = smtp_port_var.get().strip()
            smtp_user = smtp_user_var.get().strip()
            smtp_pass = smtp_pass_var.get().strip()
            original_smtp_user = self.credentials.get('smtp_user', '')

            if not is_valid_email(email_to): status_label.config(text="Invalid Recipient Email format."); return
            if not email_from: status_label.config(text="Sender Email is required for SMTP."); return
            if not is_valid_email(email_from): status_label.config(text="Invalid Sender Email format."); return
            if not smtp_server: status_label.config(text="SMTP Server is required."); return
            if not smtp_user: status_label.config(text="SMTP Username is required."); return
            try: smtp_port = int(smtp_port_str) if smtp_port_str else 587
            except ValueError: status_label.config(text="Invalid SMTP Port number."); return

            self.credentials['email_to'] = email_to
            self.credentials['email_from'] = email_from
            self.credentials['smtp_server'] = smtp_server
            self.credentials['smtp_port'] = smtp_port
            self.credentials['smtp_user'] = smtp_user

            password_action_message = ""
            password_exists_for_user = False
            try:
                 if keyring.get_password(KEYRING_SERVICE, smtp_user):
                      password_exists_for_user = True
            except Exception: pass

            if smtp_pass:
                try:
                    keyring.set_password(KEYRING_SERVICE, smtp_user, smtp_pass)
                    logger.info(f"Password saved/updated in keyring for user {smtp_user}")
                    password_action_message = "Password saved to keyring."
                except keyring.errors.NoKeyringError:
                     logger.error("Keyring backend not found.")
                     messagebox.showerror("Keyring Error", "No system keyring found. Password cannot be saved securely.", parent=dialog)
                     return
                except Exception as e:
                     logger.error(f"Error saving password to keyring: {e}")
                     messagebox.showerror("Keyring Error", f"Could not save password to keyring: {e}", parent=dialog)
                     return
            else:
                 if password_exists_for_user:
                     logger.info(f"Password field empty, keeping existing password for user {smtp_user}")
                     password_action_message = "Existing password kept."
                 else:
                     logger.info(f"Password field empty. No password stored for user {smtp_user}.")
                     password_action_message = "No password stored."
                     if smtp_user != original_smtp_user and original_smtp_user:
                         try: keyring.delete_password(KEYRING_SERVICE, original_smtp_user); logger.info(f"Deleted old password for user {original_smtp_user} from keyring.")
                         except Exception as e: logger.warning(f"Could not delete old password for {original_smtp_user} from keyring: {e}")

            if self.save_credentials():
                 messagebox.showinfo("Credentials Updated", f"Credentials updated. {password_action_message}", parent=dialog)
                 dialog.destroy()
            else:
                 messagebox.showerror("Save Error", "Failed to save non-sensitive credentials to file. Password action might have occurred.", parent=dialog)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(button_frame, text="Save", command=save_and_close).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

        parent.wait_window(dialog)

    def save_credentials(self):
        """Save non-sensitive email credentials to config file."""
        config = configparser.ConfigParser()
        non_sensitive_creds = {
            'email_to': self.credentials.get('email_to', ''),
            'email_from': self.credentials.get('email_from', ''),
            'smtp_server': self.credentials.get('smtp_server', ''),
            'smtp_port': str(self.credentials.get('smtp_port', 587)),
            'smtp_user': self.credentials.get('smtp_user', '')
        }
        config['Email'] = non_sensitive_creds
        try:
            CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f: config.write(f) # Specify encoding
            try: os.chmod(CREDENTIALS_FILE, 0o600)
            except OSError: logger.warning(f"Could not set permissions on {CREDENTIALS_FILE}.")
            debug("Non-sensitive credentials saved successfully.")
            return True
        except IOError as e:
            logger.error(f"Error saving non-sensitive credentials to {CREDENTIALS_FILE}: {e}")
            return False

    def load_schedule_data(self):
        """Read and parse schedule data, handling new 'plans' format with corrected JSON loading."""
        if not ANSWERS_FILE.exists():
             debug(f"Schedule file {ANSWERS_FILE} not found. Using defaults.")
             self.schedule = self.initialize_default_schedule()
             return self.schedule

        try:
            with open(ANSWERS_FILE, 'r', encoding='utf-8') as f: # Specify encoding
                content = f.read()

            loaded_something = False
            temp_schedule = self.initialize_default_schedule() # Start with defaults

            for day in DAYS:
                # Regex to capture content within schedule[Day]="...", handling escaped quotes \"
                pattern = rf'schedule\[{day}\]="((?:[^"\\]|\\.)*)"'
                match = re.search(pattern, content)
                if match:
                    # data_str contains the raw content between the outer quotes,
                    # including shell-escaped quotes like \"
                    data_str = match.group(1)

                    # Split based on the separator
                    parts = data_str.split(PLAN_SAVE_SEPARATOR, 1) # Split only once
                    legacy_part = parts[0]
                    json_part = parts[1] if len(parts) > 1 else None

                    # Parse legacy part (study_time|goals)
                    # Unescape shell characters (\", \\) before cleaning/using
                    legacy_part_unescaped = legacy_part.replace('\\"', '"').replace('\\\\', '\\')
                    legacy_data = legacy_part_unescaped.split('|')

                    if len(legacy_data) >= 1:
                        # Clean text after splitting
                        study_time = clean_text(legacy_data[0])
                        if not study_time or "information" in study_time:
                            study_time = DEFAULT_STUDY_TIMES.get(day, "")
                        temp_schedule[day]["study_time"] = study_time
                    if len(legacy_data) >= 2:
                        temp_schedule[day]["goals"] = clean_text(legacy_data[1]) or ""

                    # Parse JSON part for plans
                    if json_part:
                        # *** CRITICAL FIX: Unescape shell escapes (\", \\) before parsing JSON ***
                        json_part_unescaped = json_part.replace('\\"', '"').replace('\\\\', '\\')
                        json_part_cleaned = json_part_unescaped.strip()

                        if not json_part_cleaned:
                            plans_list = [] # Treat empty string as empty list
                            temp_schedule[day]["plans"] = plans_list
                        else:
                            try:
                                # Now parse the unescaped, standard JSON string
                                plans_list = json.loads(json_part_cleaned)

                                if isinstance(plans_list, list):
                                    # Basic validation of list items
                                    validated_plans = []
                                    for item in plans_list:
                                        # Ensure item is a dict before accessing keys
                                        if isinstance(item, dict):
                                            # Get name/details safely, sanitize again just in case
                                            plan_name = sanitize_input(str(item.get('name', '')))
                                            plan_details = sanitize_input(str(item.get('details', '')))
                                            if plan_name: # Only add if name is not empty after sanitization
                                                 validated_plans.append({
                                                     'name': plan_name,
                                                     'details': plan_details
                                                 })
                                            else:
                                                 logger.warning(f"Skipping plan item with empty name in {ANSWERS_FILE} for day {day} after sanitization: {item}")
                                        else:
                                             logger.warning(f"Skipping non-dictionary plan item in {ANSWERS_FILE} for day {day}: {item}")
                                    temp_schedule[day]["plans"] = validated_plans
                                else:
                                    logger.warning(f"Invalid plans format (not a list) in {ANSWERS_FILE} for day {day}. Content: '{json_part_cleaned[:100]}...'. Ignoring plans.")
                                    temp_schedule[day]["plans"] = []
                            except json.JSONDecodeError as json_err:
                                # Log the error AND the problematic string (truncated)
                                problematic_json = json_part_cleaned[:200] # Log first 200 chars
                                logger.error(f"Error decoding plans JSON in {ANSWERS_FILE} for day {day}: {json_err}. Problematic JSON part (start): '{problematic_json}...'. Ignoring plans.")
                                temp_schedule[day]["plans"] = [] # Default to empty list on error
                    else:
                        # Handle legacy format (dg_work|dg_hours|jj_work|jj_hours|goals|notes)
                        # Convert legacy work entries into plans
                        if len(legacy_data) >= 7: # Check if enough fields for legacy format
                            # Use clean_text for legacy data extraction
                            temp_schedule[day]["goals"] = clean_text(legacy_data[5]) or "" # Overwrite goals if present here
                            dg_work = legacy_data[1] if legacy_data[1] in ["yes", "no"] else "no"
                            dg_hours = clean_text(legacy_data[2])
                            jj_work = legacy_data[3] if legacy_data[3] in ["yes", "no"] else "no"
                            jj_hours = clean_text(legacy_data[4])
                            day_notes = clean_text(legacy_data[6]) # Legacy day notes

                            legacy_plans = []
                            if dg_work == "yes":
                                legacy_plans.append({"name": "Dollar General", "details": dg_hours})
                            if jj_work == "yes":
                                legacy_plans.append({"name": "JJ Pizza", "details": jj_hours})
                            if day_notes: # Add legacy notes as a plan item
                                legacy_plans.append({"name": "Note", "details": day_notes})
                            temp_schedule[day]["plans"] = legacy_plans
                            debug(f"Converted legacy work/notes to plans for {day}")
                        else:
                            # Not enough fields for legacy, assume no plans if JSON part missing
                             temp_schedule[day]["plans"] = []

                    loaded_something = True
                else:
                    # If the pattern didn't match for a day, log it and use defaults
                    logger.warning(f"Could not find schedule data entry for day {day} in {ANSWERS_FILE}. Using defaults for this day.")
                    temp_schedule[day] = self.initialize_default_schedule()[day]

            if loaded_something:
                 self.schedule = temp_schedule
                 debug(f"Successfully read schedule data for {len(self.schedule)} days (using new format)")
            else:
                 logger.warning(f"Could not parse any valid schedule entries from {ANSWERS_FILE}. Using defaults.")
                 self.schedule = self.initialize_default_schedule()

        except FileNotFoundError:
             logger.error(f"Schedule file {ANSWERS_FILE} not found. Using defaults.")
             self.schedule = self.initialize_default_schedule()
        except Exception as e:
            logger.error(f"Error reading schedule data from {ANSWERS_FILE}: {e}. Using defaults.", exc_info=True)
            self.schedule = self.initialize_default_schedule()

        return self.schedule

    def save_schedule_data(self, schedule_to_save=None):
        """Save the schedule data including plans list as JSON, with corrected escaping for shell."""
        if schedule_to_save is None:
            schedule_to_save = self.schedule

        try:
            ANSWERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if ANSWERS_FILE.exists():
                backup_file = ANSWERS_DIR / f"previous_answers.sh.bak_{int(time.time())}"
                try: shutil.copy2(ANSWERS_FILE, backup_file); debug(f"Created backup at {backup_file}")
                except Exception as backup_err: logger.warning(f"Could not create backup of {ANSWERS_FILE}: {backup_err}")

            with open(ANSWERS_FILE, 'w', encoding='utf-8') as f: # Specify encoding
                f.write(f"# Schedule data saved on {CURRENT_DATE}\n")
                f.write("days=(\n")
                for day in DAYS: f.write(f'  "{day}"\n')
                f.write(")\n\n")
                f.write("declare -A schedule\n")

                for day in DAYS:
                    day_data = schedule_to_save.get(day, self.initialize_default_schedule()[day])
                    # Sanitize data *before* saving
                    study_time = sanitize_input(day_data.get('study_time', ''))
                    goals = sanitize_input(day_data.get('goals', ''))
                    plans = day_data.get('plans', [])

                    # Ensure plans is a list of dicts with sanitized 'name' and 'details'
                    valid_plans = []
                    for p in plans:
                        if isinstance(p, dict):
                            name = sanitize_input(p.get('name', ''))
                            details = sanitize_input(p.get('details', ''))
                            if name: # Only save plans with a non-empty name
                                valid_plans.append({'name': name, 'details': details})
                            else:
                                logger.warning(f"Skipping plan with empty name during save for {day}: {p}")
                        else:
                            logger.warning(f"Skipping non-dictionary plan item during save for {day}: {p}")

                    if len(valid_plans) != len(plans):
                        logger.warning(f"Some invalid plan items detected for {day} during save. Only valid items saved.")

                    try:
                        # Generate standard JSON string
                        plans_json = json.dumps(valid_plans, ensure_ascii=False)
                    except TypeError as json_err:
                         logger.error(f"Could not serialize plans to JSON for day {day}: {json_err}. Saving empty plans list.")
                         plans_json = "[]"

                    # Escape potential shell-problematic characters within study_time and goals ONLY
                    escaped_study_time = study_time.replace('\\', '\\\\').replace('"', '\\"')
                    escaped_goals = goals.replace('\\', '\\\\').replace('"', '\\"')

                    # Escape double quotes and backslashes within the JSON string for shell compatibility
                    shell_safe_plans_json = plans_json.replace('\\', '\\\\').replace('"', '\\"')

                    # Combine parts using the shell-safe JSON
                    combined_data = f"{escaped_study_time}|{escaped_goals}{PLAN_SAVE_SEPARATOR}{shell_safe_plans_json}"

                    # Write the shell assignment.
                    f.write(f'schedule[{day}]="{combined_data}"\n')

            try: os.chmod(ANSWERS_FILE, 0o600)
            except OSError: logger.warning(f"Could not set permissions on {ANSWERS_FILE}.")

            debug(f"Schedule data saved to {ANSWERS_FILE} (with corrected JSON shell escaping)")
            self.schedule = schedule_to_save # Update internal state
            return True
        except Exception as e:
            logger.error(f"Error saving schedule data: {e}", exc_info=True)
            return False

    def load_notes(self):
        """Load additional notes from the notes file."""
        if NOTES_FILE.exists() and NOTES_FILE.stat().st_size > 0:
            try:
                with open(NOTES_FILE, 'r', encoding='utf-8') as f: self.additional_notes = f.read() # Specify encoding
                debug("Loaded additional notes.")
            except Exception as e:
                logger.error(f"Error reading notes file {NOTES_FILE}: {e}")
                self.additional_notes = ""
        else: self.additional_notes = ""
        return self.additional_notes

    def save_notes(self, notes_content=None):
        """Save additional notes to the notes file."""
        if notes_content is None: notes_content = self.additional_notes
        try:
            NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Sanitize notes before saving? Maybe not, allow more freedom here.
            with open(NOTES_FILE, 'w', encoding='utf-8') as f: f.write(notes_content) # Specify encoding
            try: os.chmod(NOTES_FILE, 0o600)
            except OSError: logger.warning(f"Could not set permissions on {NOTES_FILE}.")
            self.additional_notes = notes_content
            debug(f"Notes saved to {NOTES_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving notes: {e}")
            return False

    def generate_text_schedule(self, schedule_data=None):
        """Generate a beautifully formatted plain text schedule."""
        if schedule_data is None:
            schedule_data = self.schedule
        
        output = []
        
        # Header with date
        output.append("╔═══════════════════════════════════════════════════════════════════════╗")
        output.append("║                         WEEKLY SCHEDULE                               ║")
        output.append(f"║                      {CURRENT_DATE.center(25)}                     ║")
        output.append("╚═══════════════════════════════════════════════════════════════════════╝")
        output.append("")
        
        # Process each day
        for day_index, day in enumerate(DAYS):
            day_data = schedule_data.get(day, {})
            study_time = day_data.get('study_time', '')
            goals = day_data.get('goals', '')
            plans = day_data.get('plans', [])
            
            # Day header with nice formatting
            day_header = f" {day.upper()} "
            if day_index == 0:  # Monday
                output.append(f"┌─────────────────────────── {day_header} ───────────────────────────┐")
            else:
                output.append(f"├─────────────────────────── {day_header} ───────────────────────────┤")
            
            # Check if day has any content
            visible_plans = [p for p in plans if isinstance(p, dict) and p.get('details', '').strip()]
            has_content = study_time or goals or visible_plans
            
            if not has_content:
                output.append("│                                                                       │")
                output.append("│                          No schedule set                              │")
                output.append("│                                                                       │")
            else:
                # Study time section
                if study_time:
                    output.append("│                                                                       │")
                    output.append("│  📚 STUDY TIME                                                        │")
                    output.append(f"│     {study_time:<62} │")
                
                # Goals section
                if goals:
                    if study_time:
                        output.append("│                                                                       │")
                    else:
                        output.append("│                                                                       │")
                    output.append("│  🎯 GOALS                                                             │")
                    
                    # Word wrap goals if needed
                    wrapped_goals = textwrap.wrap(goals, width=60)
                    for line in wrapped_goals:
                        output.append(f"│     {line:<62} │")
                
                # Plans section
                if plans:
                    # Filter out plans with empty details
                    visible_plans = [p for p in plans if isinstance(p, dict) and p.get('details', '').strip()]
                    
                    if visible_plans:
                        if study_time or goals:
                            output.append("│                                                                       │")
                        else:
                            output.append("│                                                                       │")
                        output.append("│  📋 PLANS & ACTIVITIES                                                │")
                        
                        for i, plan in enumerate(visible_plans):
                            plan_name = plan.get('name', 'Unnamed')
                            plan_details = plan.get('details', '')
                            
                            # Format plan with bullet point
                            output.append(f"│     • {plan_name:<59} │")
                            
                            # Add details (we know they exist because we filtered)
                            wrapped_details = textwrap.wrap(plan_details, width=57)
                            for line in wrapped_details:
                                output.append(f"│       {line:<60} │")
                        
                        # Add spacing after last plan if there are multiple
                        if len(visible_plans) > 1:
                            output.append("│                                                                       │")
                
                # Add bottom padding for content days
                if not goals and not visible_plans and study_time:
                    output.append("│                                                                       │")
        
        # Close the last day box
        output.append("└───────────────────────────────────────────────────────────────────────┘")
        output.append("")
        
        # Summary section
        output.append("═══════════════════════════════════════════════════════════════════════")
        output.append("                           WEEK SUMMARY                                ")
        output.append("═══════════════════════════════════════════════════════════════════════")
        output.append("")
        
        # Calculate weekly statistics
        total_study_hours = 0
        total_plans = 0
        days_with_goals = 0
        
        for day in DAYS:
            day_data = schedule_data.get(day, {})
            
            # Count study hours (simple parsing)
            study_time = day_data.get('study_time', '')
            if study_time:
                # Try to extract hours from format like "11:00-3:00"
                time_match = re.match(r'(\d+):(\d+)-(\d+):(\d+)', study_time)
                if time_match:
                    start_hour = int(time_match.group(1))
                    start_min = int(time_match.group(2))
                    end_hour = int(time_match.group(3))
                    end_min = int(time_match.group(4))
                    
                    # Handle PM times (simple assumption: if end < start, it's PM)
                    if end_hour < start_hour:
                        end_hour += 12
                    
                    hours = (end_hour + end_min/60) - (start_hour + start_min/60)
                    total_study_hours += hours
            
            # Count plans (only those with details)
            plans = day_data.get('plans', [])
            visible_plans = [p for p in plans if isinstance(p, dict) and p.get('details', '').strip()]
            total_plans += len(visible_plans)
            
            # Count days with goals
            if day_data.get('goals', ''):
                days_with_goals += 1
        
        # Display summary
        output.append(f"  📊 Total Study Hours Scheduled: {total_study_hours:.1f} hours")
        output.append(f"  📋 Total Plans/Activities: {total_plans}")
        output.append(f"  🎯 Days with Goals Set: {days_with_goals}/7")
        output.append("")
        
        # Footer
        output.append("───────────────────────────────────────────────────────────────────────")
        output.append(f"Generated on {CURRENT_DATE} • Schedule Maker v6")
        output.append("───────────────────────────────────────────────────────────────────────")
        
        return "\n".join(output)

    def generate_reminders(self, schedule_data=None):
        """Generate beautifully formatted reminders text."""
        if schedule_data is None:
            schedule_data = self.schedule
        
        output = []
        
        # Header
        output.append("╔═══════════════════════════════════════════════════════════════════════╗")
        output.append("║                    WEEKLY GOALS & REMINDERS                           ║")
        output.append(f"║                      {CURRENT_DATE.center(25)}                     ║")
        output.append("╚═══════════════════════════════════════════════════════════════════════╝")
        output.append("")
        
        # Check if there's any content
        has_any_content = False
        for day in DAYS:
            day_data = schedule_data.get(day, {})
            plans = day_data.get('plans', [])
            visible_plans = [p for p in plans if isinstance(p, dict) and p.get('details', '').strip()]
            if day_data.get('goals') or visible_plans:
                has_any_content = True
                break
        
        if not has_any_content:
            output.append("┌───────────────────────────────────────────────────────────────────────┐")
            output.append("│                                                                       │")
            output.append("│              No specific goals or plans set for this week             │")
            output.append("│                                                                       │")
            output.append("│                     +   +                   +   +                     │")
            output.append("│                       _                       _                       │")
            output.append("└───────────────────────────────────────────────────────────────────────┘")
        else:
            # Group by priority/importance
            all_goals = []
            all_plans = []
            
            for day in DAYS:
                day_data = schedule_data.get(day, {})
                goals = day_data.get('goals', '')
                plans = day_data.get('plans', [])
                
                if goals:
                    all_goals.append((day, goals))
                if plans:
                    for plan in plans:
                        if isinstance(plan, dict) and plan.get('details', '').strip():
                            all_plans.append((day, plan))
            
            # Display Goals section
            if all_goals:
                output.append("┌─────────────────────── 🎯 WEEKLY GOALS ──────────────────────────────┐")
                output.append("│                                                                       │")
                
                for day, goal in all_goals:
                    output.append(f"│  {day:<12} {goal[:54]:<54} │")
                    # Wrap long goals
                    if len(goal) > 54:
                        wrapped = textwrap.wrap(goal[54:], width=54)
                        for line in wrapped:
                            output.append(f"│  {'':12} {line:<54} │")
                    output.append("│                                                                       │")
                
                output.append("└───────────────────────────────────────────────────────────────────────┘")
                output.append("")
            
            # Display Plans section
            if all_plans:
                output.append("┌────────────────────── 📋 WEEKLY PLANS ───────────────────────────────┐")
                output.append("│                                                                       │")
                
                # Group plans by type
                work_plans = []
                appointment_plans = []
                eat_plans = []
                sleeping_plans = []
                pray_plans = []
                break_plans = []
                study_plans = []
                youtube_plans = []
                play_plans = []
                other_plans = []
                
                for day, plan in all_plans:
                    plan_name = plan.get('name', '').lower()
                    if 'work' in plan_name or 'dollar general' in plan_name or 'jj' in plan_name:
                        work_plans.append((day, plan))
                    elif 'appointment' in plan_name or 'appt' in plan_name or 'meeting' in plan_name:
                        appointment_plans.append((day, plan))
                    elif 'eat' in plan_name or 'meal' in plan_name or 'lunch' in plan_name or 'dinner' in plan_name:
                        eat_plans.append((day, plan))
                    elif 'sleep' in plan_name or 'night' in plan_name or 'bedtime' in plan_name or 'nap' in plan_name or 'rest' in plan_name:
                        sleeping_plans.append((day, plan))
                    elif 'pray' in plan_name or 'worship' in plan_name or 'rosary' in plan_name or 'meditation' in plan_name:
                        pray_plans.append((day, plan))
                    elif 'break' in plan_name or 'relax' in plan_name or 'chill' in plan_name:
                        break_plans.append((day, plan))
                    elif 'study' in plan_name or 'homework' in plan_name or 'assignment' in plan_name or 'revision' in plan_name or 'research' in plan_name:
                        study_plans.append((day, plan))
                    elif 'play' in plan_name or 'game' in plan_name or 'gaming' in plan_name or 'fun' in plan_name or 'outside' in plan_name:
                        play_plans.append((day, plan))
                    elif 'youtube' in plan_name or 'video' in plan_name or 'watch' in plan_name:
                        youtube_plans.append((day, plan))
                    else:
                        other_plans.append((day, plan))
                
                # Display work plans
                if work_plans:
                    output.append("│  🤯 WORK SCHEDULE                                                     │")
                    output.append("│  ─────────────────                                                    │")
                    for day, plan in work_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display appointments
                if appointment_plans:
                    output.append("│  📬 APPOINTMENTS                                                      │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in appointment_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display eating plans
                if eat_plans:
                    output.append("│  🍽️ EATING PLANS                                                     │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in eat_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display YouTube plans
                if youtube_plans:
                    output.append("│  📺 YOUTUBE VIDEOS                                                    │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in youtube_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display sleeping plans
                if sleeping_plans:
                    output.append("│  😪 Sleeping                                                      │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in sleeping_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display praying plans
                if pray_plans:
                    output.append("│  🙏 PRAYING & WORSHIP                                                │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in pray_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display break plans
                if break_plans:
                    output.append("│  🛌 BREAKS & RELAXATION                                               │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in break_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display study plans
                if study_plans:
                    output.append("│  📚 STUDY PLANS                                                      │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in study_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display play plans
                if play_plans:
                    output.append("│  🎮 PLAY PLANS                                                        │")
                    output.append("│  ───────────────                                                      │")
                    for day, plan in play_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                # Display other plans
                if other_plans:
                    output.append("│  📌 OTHER ACTIVITIES                                                  │")
                    output.append("│  ──────────────────                                                   │")
                    for day, plan in other_plans:
                        name = plan.get('name', 'Unnamed')
                        details = plan.get('details', '')
                        output.append(f"│  • {day:<10} {name:<25} {details[:23]:<23} │")
                    output.append("│                                                                       │")
                
                output.append("└───────────────────────────────────────────────────────────────────────┘")
        
        output.append("")
        output.append("════_^_═══════════_^_═══════════_^_═══════════_^_══════════════════════")
        output.append("💡 (x-x)!     💡 (x-x)!     💡 (x-x)!     💡 (x-x)!")
        output.append("═══=(_)══════════=(_)══════════=(_)══════════=(_)══════════════════════")
        
        return "\n".join(output)
    
    def generate_html_email(self, schedule_data=None, notes_content=None):
        """Generates HTML email content with better compatibility for Gmail and Outlook."""
        if schedule_data is None:
            schedule_data = self.schedule
        if notes_content is None:
            notes_content = self.additional_notes

        # Create HTML with table-based layout for better email client support
        html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Weekly Schedule - {CURRENT_DATE}</title>
        <!--[if mso]>
        <noscript>
            <xml>
                <o:OfficeDocumentSettings>
                    <o:PixelsPerInch>96</o:PixelsPerInch>
                </o:OfficeDocumentSettings>
            </xml>
        </noscript>
        <![endif]-->
        <style type="text/css">
            /* Reset styles */
            body, table, td, a {{ text-size-adjust: 100%; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
            table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
            img {{ border: 0; line-height: 100%; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; }}
            
            /* Remove default styling */
            body {{ margin: 0; padding: 0; width: 100% !important; min-width: 100%; }}
            
            /* Email client specific styles */
            .ReadMsgBody {{ width: 100%; }}
            .ExternalClass {{ width: 100%; }}
            .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div {{ line-height: 100%; }}
            
            /* Outlook specific */
            table {{ border-collapse: collapse !important; }}
            
            /* Mobile styles */
            @media screen and (max-width: 600px) {{
                .mobile-hide {{ display: none !important; }}
                .mobile-center {{ text-align: center !important; }}
                .container {{ width: 100% !important; max-width: 100% !important; }}
                .day-column {{ width: 100% !important; display: block !important; margin-bottom: 20px !important; }}
                .day-table {{ width: 100% !important; }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f6f9fc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <!-- Wrapper table -->
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f6f9fc;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    
                    <!-- Container table -->
                    <table cellpadding="0" cellspacing="0" border="0" width="100%" class="container" style="max-width: 800px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);">
                        
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 30px; text-align: center; background-color: #1a365d; border-radius: 8px 8px 0 0;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; line-height: 1.2;">My Weekly Schedule</h1>
                                <p style="margin: 10px 0 0 0; color: #e2e8f0; font-size: 16px;">{CURRENT_DATE}</p>
                            </td>
                        </tr>
                        
                        <!-- Schedule Content -->
                        <tr>
                            <td style="padding: 30px;">
                                
                                <!-- Days Grid -->
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    <tr>
                                        <td style="padding-bottom: 30px;">
                                            
                                            <!-- Mobile responsive: Stack on small screens -->
                                            <!--[if mso]>
                                            <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
                                            <![endif]-->
                                            
                                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="table-layout: 100%;">
    """

        # Process days and create content
        day_colors = {
            "Monday": "#3b82f6", "Tues": "#8b5cf6", "Wed": "#10b981",
            "Thur": "#f59e0b", "Fri": "#ef4444", "Sat": "#6366f1", "Sun": "#ec4899"
        }
        
        # Create rows for the schedule (7 days split into rows for better mobile display)
        days_per_row = 3 if len(DAYS) > 4 else len(DAYS)
        day_index = 0
        
        while day_index < len(DAYS):
            html_content += '<tr>'
            
            for i in range(days_per_row):
                if day_index >= len(DAYS):
                    # Add empty cell for alignment
                    html_content += '<td class="day-column" width="33%" style="padding: 0 5px;"></td>'
                else:
                    day = DAYS[day_index]
                    day_data = schedule_data.get(day, {})
                    study_time = day_data.get('study_time', '')
                    goals = day_data.get('goals', '')
                    plans = day_data.get('plans', [])
                    color = day_colors.get(day, "#64748b")
                    
                    html_content += f"""
                        <td class="day-column" width="33%" valign="top" style="padding: 0 5px 15px 5px;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" class="day-table" style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden;">
                                <!-- Day Header -->
                                <tr>
                                    <td style="background-color: {color}; padding: 12px 15px; text-align: center;">
                                        <h3 style="margin: 0; color: #ffffff; font-size: 18px; font-weight: 600;">{day}</h3>
                                    </td>
                                </tr>
                                <!-- Day Content -->
                                <tr>
                                    <td style="padding: 15px;">
    """
                    
                    # Add study time if present
                    if study_time:
                        html_content += f"""
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 12px;">
                                            <tr>
                                                <td style="border-left: 3px solid {color}; padding-left: 12px;">
                                                    <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 600;">Study Time</p>
                                                    <p style="margin: 0; color: #6b7280; font-size: 13px;">{html_escaper.escape(study_time)}</p>
                                                </td>
                                            </tr>
                                        </table>
    """
                    
                    # Add goals if present
                    if goals:
                        html_content += f"""
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 12px;">
                                            <tr>
                                                <td style="border-left: 3px solid {color}; padding-left: 12px;">
                                                    <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 600;">Goals</p>
                                                    <p style="margin: 0; color: #6b7280; font-size: 13px;">{html_escaper.escape(goals)}</p>
                                                </td>
                                            </tr>
                                        </table>
    """
                    
                    # Add plans (only those with details)
                    visible_plans = [p for p in plans if isinstance(p, dict) and p.get('details', '').strip()]
                    for plan in visible_plans:
                        plan_name = plan.get('name', 'Unnamed Plan')
                        plan_details = plan.get('details', '')
                        html_content += f"""
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 12px;">
                                            <tr>
                                                <td style="border-left: 3px solid {color}; padding-left: 12px;">
                                                    <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 600;">{html_escaper.escape(plan_name)}</p>
                                                    <p style="margin: 0; color: #6b7280; font-size: 13px;">{html_escaper.escape(plan_details)}</p>
                                                </td>
                                            </tr>
                                        </table>
    """
                    
                    # If no content for the day
                    visible_plans = [p for p in plans if isinstance(p, dict) and p.get('details', '').strip()]
                    if not study_time and not goals and not visible_plans:
                        html_content += """
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                            <tr>
                                                <td style="padding: 8px 0;">
                                                    <p style="margin: 0; color: #9ca3af; font-size: 13px; font-style: italic; text-align: center;">No schedule set</p>
                                                </td>
                                            </tr>
                                        </table>
    """
                    
                    html_content += """
                                    </td>
                                </tr>
                            </table>
                        </td>
    """
                    day_index += 1
            
            html_content += '</tr>'
            
            # Add spacing between rows
            if day_index < len(DAYS):
                html_content += '<tr><td colspan="3" style="height: 10px;"></td></tr>'
        
        html_content += """
                                            </table>
                                            
                                            <!--[if mso]>
                                            </tr></table>
                                            <![endif]-->
                                            
                                        </td>
                                    </tr>
                                </table>
    """
        
        # Add notes section if present
        if notes_content and notes_content.strip():
            escaped_notes = html_escaper.escape(notes_content.strip())
            html_content += f"""
                                <!-- Notes Section -->
                                <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 30px;">
                                    <tr>
                                        <td style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 20px;">
                                            <h3 style="margin: 0 0 12px 0; color: #1f2937; font-size: 18px; font-weight: 600;">Additional Notes</h3>
                                            <pre style="margin: 0; color: #4b5563; font-size: 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; white-space: pre-wrap; word-wrap: break-word;">{escaped_notes}</pre>
                                        </td>
                                    </tr>
                                </table>
    """
        
        html_content += f"""
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                <p style="margin: 0; color: #6b7280; font-size: 13px;">Schedule generated on {CURRENT_DATE}</p>
                            </td>
                        </tr>
                        
                    </table>
                    <!-- End Container -->
                    
                </td>
            </tr>
        </table>
        <!-- End Wrapper -->
    </body>
    </html>
    """
        
        # Now inline the CSS using css_inline
        try:
            # Configure inliner for email compatibility
            inliner = css_inline.CSSInliner(
                keep_style_tags=True,  # Keep style tags for clients that support them
                keep_link_tags=False,  # Remove link tags
                base_url=None,
                load_remote_stylesheets=False,
                extra_css=None,
                preallocate_node_capacity=1000
            )
            inlined_html = inliner.inline(html_content)
            logger.info("Successfully generated email-compatible HTML content.")
            return inlined_html
        except Exception as e:
            logger.error(f"Error during CSS inlining: {e}", exc_info=True)
            # Return the non-inlined HTML if inlining fails
            return html_content

    def save_generated_files(self):
        """Generate and save the schedule.txt, reminders.txt, and HTML files."""
        files_saved = {}
        try:
            SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            HTML_FILE.parent.mkdir(parents=True, exist_ok=True)

            schedule_text = self.generate_text_schedule()
            with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f: f.write(schedule_text) # Specify encoding
            logger.info(f"Schedule saved to {SCHEDULE_FILE}")
            files_saved['schedule'] = str(SCHEDULE_FILE)

            reminders_text = self.generate_reminders()
            with open(REMINDERS_FILE, 'w', encoding='utf-8') as f: f.write(reminders_text) # Specify encoding
            logger.info(f"Reminders saved to {REMINDERS_FILE}")
            files_saved['reminders'] = str(REMINDERS_FILE)

            html_content = self.generate_html_email(notes_content=self.additional_notes)
            with open(HTML_FILE, 'w', encoding='utf-8') as f: f.write(html_content) # Specify encoding
            try: os.chmod(HTML_FILE, 0o600)
            except OSError: logger.warning(f"Could not set permissions on {HTML_FILE}.")
            logger.info(f"HTML saved to {HTML_FILE}")
            files_saved['html'] = str(HTML_FILE)

            return files_saved
        except Exception as e:
            logger.error(f"Error generating/saving output files: {e}", exc_info=True)
            return files_saved

    def send_email_with_attachments(self):
        """Send the HTML email with generated file attachments using keyring password."""
        creds = self.credentials
        if not all(creds.get(k) for k in ['email_to', 'email_from', 'smtp_user', 'smtp_server']):
            logger.warning("Email recipient/sender/user/server not configured. Cannot send email.")
            return False, "Email recipient/sender/user/server not configured."

        password = None
        try:
             password = keyring.get_password(KEYRING_SERVICE, creds['smtp_user'])
             if not password:
                  logger.error(f"Password for {creds['smtp_user']} not found in keyring. Cannot send email.")
                  return False, f"Password for {creds['smtp_user']} not found in keyring."
        except keyring.errors.NoKeyringError:
             logger.error("Keyring backend not found.")
             return False, "Keyring backend not found. Cannot send email."
        except Exception as e:
             logger.error(f"Error accessing keyring: {e}")
             return False, f"Error retrieving password from keyring: {e}"

        generated_files = self.save_generated_files()
        if not generated_files.get('html'):
             logger.error("HTML file generation failed.")
             return False, "Failed to generate HTML email content."

        html_content = ""
        try:
             with open(generated_files['html'], 'r', encoding='utf-8') as f: html_content = f.read() # Specify encoding
        except Exception as e:
             logger.error(f"Could not read generated HTML file {generated_files['html']}: {e}")
             return False, "Failed to read generated HTML file."

        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = f"Weekly Schedule - {CURRENT_DATE}"
            msg['From'] = f"Schedule Maker <{creds['email_from']}>"
            msg['To'] = creds['email_to']
            part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part)

            for key, filepath in generated_files.items():
                if Path(filepath).exists():
                    try:
                        with open(filepath, 'rb') as f:
                            attachment = MIMEApplication(f.read(), Name=os.path.basename(filepath))
                        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filepath))
                        msg.attach(attachment)
                        debug(f"Attached {filepath}")
                    except Exception as attach_err:
                         logger.warning(f"Could not attach file {filepath}: {attach_err}")

            logger.info(f"Connecting to {creds['smtp_server']}:{creds['smtp_port']}")
            server = smtplib.SMTP(creds['smtp_server'], creds['smtp_port'])
            server.ehlo()
            server.starttls()
            server.ehlo()
            logger.info(f"Logging in as {creds['smtp_user']}")
            server.login(creds['smtp_user'], password) # Use keyring password
            logger.info(f"Sending email to: {creds['email_to']}")
            server.send_message(msg)
            server.quit()
            logger.info("SMTP connection closed.")
            return True, f"Email sent successfully to {creds['email_to']}."

        except smtplib.SMTPAuthenticationError:
             logger.error("SMTP Authentication Error.")
             return False, "Email Authentication Failed: Check username/password (retrieved from keyring)."
        except smtplib.SMTPConnectError as e:
             logger.error(f"SMTP Connection Error: {e}")
             return False, f"Email Connection Failed: Could not connect to server."
        except smtplib.SMTPServerDisconnected:
             logger.error("SMTP Server Disconnected unexpectedly.")
             return False, "Email Failed: Server disconnected unexpectedly."
        except smtplib.SMTPException as e:
             logger.error(f"SMTP Error occurred: {e}")
             return False, f"Email Failed: SMTP Error - {e}"
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            if self._try_backup_mail_command(generated_files.get('html', ''), creds['email_to']):
                 return True, "Email sent using backup 'mail' command."
            else:
                 return False, f"Email Failed: {e}"

    def _try_backup_mail_command(self, html_filepath, recipient_email):
        """Attempt to send email using the system 'mail' command as a fallback."""
        if not html_filepath or not Path(html_filepath).exists(): return False
        mail_path = shutil.which("mail")
        if not mail_path: logger.warning("'mail' command not found."); return False
        try:
            subject = f"Weekly Schedule - {CURRENT_DATE}"
            cmd = [mail_path, "-s", subject, "-a", "Content-Type: text/html; charset=utf-8"]
            if Path(SCHEDULE_FILE).exists(): cmd.extend(["-A", str(SCHEDULE_FILE)])
            if Path(REMINDERS_FILE).exists(): cmd.extend(["-A", str(REMINDERS_FILE)])
            if Path(HTML_FILE).exists(): cmd.extend(["-A", str(HTML_FILE)])
            cmd.append(recipient_email)
            logger.info(f"Attempting backup mail command: {' '.join(cmd)}")
            with open(html_filepath, 'r', encoding='utf-8') as f_html: # Specify encoding
                process = subprocess.run(cmd, stdin=f_html, capture_output=True, text=True, encoding='utf-8')
            if process.returncode == 0: logger.info("Email sent using backup 'mail' command."); return True
            else: logger.error(f"Backup 'mail' command failed. RC: {process.returncode}. Stdout: {process.stdout}. Stderr: {process.stderr}"); return False
        except Exception as backup_error:
            logger.error(f"Backup email method failed: {backup_error}", exc_info=True); return False