#!/usr/bin/env python3

import sys
import os
from config import Color, DAYS, DEFAULT_STUDY_TIMES, ANSWERS_FILE
from utils import sanitize_input
from schedule_manager import ScheduleManager

def print_header(message):
    """Print a formatted header (CLI only)"""
    if sys.stdout.isatty():
        print(f"{Color.BLUE}{'=' * 55}{Color.NC}")
        print(f"{Color.BLUE}{message.center(55)}{Color.NC}")
        print(f"{Color.BLUE}{'=' * 55}{Color.NC}")
        print()
    else:
        print(f"\n=== {message} ===\n")


def ask_yes_no(question, default=None):
    """Ask a yes/no question and return True for yes, False for no (CLI only)"""
    if not sys.stdin.isatty(): 
        return default == "yes"  # Non-interactive, return default

    if default == "yes": 
        prompt, default_answer = f"{question} [Yes] (y/n): ", "y"
    elif default == "no": 
        prompt, default_answer = f"{question} [No] (y/n): ", "n"
    else: 
        prompt, default_answer = f"{question} (y/n): ", None

    while True:
        try:
            answer = input(prompt).lower().strip()
            if not answer and default_answer: 
                answer = default_answer
            if answer in ['y', 'yes']: 
                return True
            elif answer in ['n', 'no']: 
                return False
            else: 
                print("Please answer yes (y) or no (n).")
        except EOFError: 
            print("\nInput interrupted. Assuming 'no'.")
            return False


def collect_day_info_cli(day, day_data):
    """Collect schedule information for a specific day via CLI, including plans"""
    print_header(f"SCHEDULE FOR {day}")

    # --- Study information ---
    print(f"{Color.YELLOW}Study information for {day}:{Color.NC}")
    default_study_time = day_data.get("study_time", DEFAULT_STUDY_TIMES.get(day, ""))
    study_time = sanitize_input(input(f"Study time [{default_study_time}]: ").strip() or default_study_time)

    # --- Study goals ---
    default_goals = day_data.get("goals", "")
    print(f"Enter specific study goals for {day} (press Enter for none):")
    study_goals = sanitize_input(input(f"[{default_goals}]: ").strip() or default_goals)

    # --- Plans (Work, Appointments, etc.) ---
    print(f"{Color.YELLOW}Plans for {day}:{Color.NC}")
    current_plans = list(day_data.get("plans", []))  # Get existing plans for potential editing (simple overwrite here)
    new_plans = []

    # Display existing plans first (if any)
    if current_plans:
        print("Existing plans:")
        for i, plan in enumerate(current_plans):
            print(f"  {i+1}. {plan.get('name', 'N/A')}: {plan.get('details', 'N/A')}")
        if not ask_yes_no("Clear existing plans and enter new ones?", default="no"):
            new_plans = current_plans  # Keep existing if user says no
            print("Keeping existing plans.")
        else:
            print("Clearing existing plans.")

    # If not keeping existing, or if none existed, ask for new plans
    if not new_plans:  # This condition is met if user chose to clear or if no plans existed
        while True:
            add_more = ask_yes_no(f"Add a plan for {day}?", default="yes" if not new_plans else "no")  # Default yes for first plan
            if not add_more:
                break

            plan_name = sanitize_input(input("  Plan Name: ").strip())
            plan_details = sanitize_input(input("  Plan Details (e.g., hours, location): ").strip())

            if plan_name:  # Only add if name is provided
                new_plans.append({"name": plan_name, "details": plan_details})
            else:
                print(f"{Color.YELLOW}Plan name cannot be empty. Plan not added.{Color.NC}")

    # Return updated data
    return {
        "study_time": study_time,
        "goals": study_goals,
        "plans": new_plans  # Use the collected/kept plans
    }


def add_notes_cli(manager):
    """Prompt for and save additional notes via CLI"""
    print_header("ADDITIONAL SCHEDULE NOTES")
    previous_notes = manager.load_notes()
    if previous_notes:
        print("Previous notes:")
        print(previous_notes)
        print("-" * 20)
        if not ask_yes_no("Would you like to update/replace these notes?", "no"):
            print(f"{Color.GREEN}Keeping previous notes.{Color.NC}")
            return
    print("Enter any additional notes for this week (type 'END' on a line by itself when finished):")
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END": 
                break
            if line == "DIEEEEE": 
                lines.append(line)
            else: 
                lines.append(sanitize_input(line))
        except EOFError: 
            print("\nInput interrupted. Saving notes entered so far.")
            break

    new_notes = "\n".join(lines)
    if manager.save_notes(new_notes):
        print(f"{Color.GREEN}Notes saved!{Color.NC}")
        manager.save_generated_files()  # Regenerate files
        print(f"{Color.GREEN}Output files regenerated with updated notes.{Color.NC}")
    else:
        print(f"{Color.RED}Failed to save notes.{Color.NC}")


def run_cli(manager, auto_mode=False):
    """Main function for the Command-Line Interface"""
    if sys.stdout.isatty() and not auto_mode:
        os.system('clear' if os.name == 'posix' else 'cls')

    print_header("WEEKLY SCHEDULE GENERATOR (CLI)")

    # Load credentials (prompt only if essential info missing and not auto mode)
    prompt_creds = not auto_mode and (not manager.credentials.get('email_from') or not manager.credentials.get('smtp_user'))
    manager.load_credentials(prompt_if_missing=prompt_creds)

    current_schedule = manager.load_schedule_data()  # Load existing data (new format aware)

    if not auto_mode:
        load_previous = False
        if ANSWERS_FILE.exists():
            if ask_yes_no("Load your previous schedule as a starting point?", "yes"):
                print(f"{Color.GREEN}Previous schedule loaded. You can now update it.{Color.NC}")
                load_previous = True
            else:
                print(f"{Color.YELLOW}Starting with a default schedule.{Color.NC}")
                current_schedule = manager.initialize_default_schedule()  # Reset to default
        else:
            print(f"{Color.YELLOW}No previous schedule found. Creating a new one.{Color.NC}")
            current_schedule = manager.initialize_default_schedule()

        # Collect information for each day
        updated_schedule = {}
        try:
            for day in DAYS:
                # Pass the correct schedule data (either loaded or default)
                day_data_to_edit = current_schedule.get(day, manager.initialize_default_schedule()[day])
                updated_schedule[day] = collect_day_info_cli(day, day_data_to_edit)
                print()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Color.YELLOW}Input interrupted. Saving progress made so far...{Color.NC}")
            if updated_schedule:
                for day_to_fill in DAYS:
                    if day_to_fill not in updated_schedule:
                        updated_schedule[day_to_fill] = current_schedule.get(day_to_fill, manager.initialize_default_schedule()[day_to_fill])
                manager.save_schedule_data(updated_schedule)
            print(f"{Color.YELLOW}Exiting CLI mode.{Color.NC}")
            return

        manager.save_schedule_data(updated_schedule)  # Save the collected data

    # Generate and save output files (always do this after potential updates or in auto mode)
    saved_files = manager.save_generated_files()
    if saved_files.get('schedule'): 
        print(f"{Color.GREEN}Schedule saved to {saved_files['schedule']}{Color.NC}")
    if saved_files.get('reminders'): 
        print(f"{Color.GREEN}Reminders saved to {saved_files['reminders']}{Color.NC}")
    if saved_files.get('html'): 
        print(f"{Color.GREEN}HTML saved to {saved_files['html']}{Color.NC}")

    if not auto_mode:
        while True:
            print("\n" + "="*30)
            print("ACTIONS:")
            print(f"  (N)otes       - Add/Update additional notes")
            print(f"  (E)mail       - Send schedule email to {manager.credentials.get('email_to', 'N/A')}")
            print(f"  (C)onfigure   - Change email settings")
            print(f"  (Q)uit        - Exit")
            print("="*30)
            try: 
                action = input("Choose action: ").lower().strip()
            except EOFError: 
                print("\nInput interrupted. Exiting.")
                action = 'q'

            if action == 'n': 
                add_notes_cli(manager)
            elif action == 'e':
                print(f"Attempting to send email to {manager.credentials.get('email_to', 'N/A')}...")
                success, message = manager.send_email_with_attachments()
                print(f"{Color.GREEN if success else Color.RED}{message}{Color.NC}")
                if not success and ("not found in keyring" in message or "Authentication Failed" in message or "not configured" in message):
                    if ask_yes_no("Configure email settings now?", "yes"): 
                        manager._prompt_credentials_cli()
            elif action == 'c':
                manager._prompt_credentials_cli()
                manager.save_generated_files()  # Regenerate files after config
                print(f"{Color.GREEN}Output files regenerated.{Color.NC}")
            elif action == 'q': 
                break
            else: 
                print(f"{Color.YELLOW}Invalid action.{Color.NC}")

    print_header("SCHEDULE GENERATION COMPLETE")
    if auto_mode: 
        print(f"{Color.GREEN}Schedule processed in auto mode.{Color.NC}")
    else: 
        print(f"{Color.GREEN}Exiting Schedule Maker.{Color.NC}")