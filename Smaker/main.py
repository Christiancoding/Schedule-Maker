import sys
import tkinter as tk
from schedule_manager import ScheduleManager
from cli_interface import run_cli
from gui_interface import ScheduleGUI
from config import Color
from config import logger
from tkinter import messagebox

# =============================================================================
# == Main Execution Block
# =============================================================================

if __name__ == "__main__":
    manager = ScheduleManager()
    interface_mode = "ask"
    auto_mode_cli = False

    if "-cli" in sys.argv: interface_mode = "cli"
    elif "-gui" in sys.argv: interface_mode = "gui"
    elif "-auto" in sys.argv: interface_mode = "cli"; auto_mode_cli = True; print("Running in automated CLI mode.")

    if interface_mode == "ask" and sys.stdin.isatty() and not auto_mode_cli:
        while True:
            try:
                choice = input("Choose interface (cli/gui): ").lower().strip()
                if choice in ["cli", "gui"]: interface_mode = choice; break
                else: print("Invalid choice. Please enter 'cli' or 'gui'.")
            except EOFError: print("\nInput interrupted. Defaulting to CLI."); interface_mode = "cli"; break
            except KeyboardInterrupt: print("\nOperation cancelled. Exiting."); sys.exit(0)
    elif interface_mode == "ask":
         logger.info("Non-interactive environment or mode not specified. Defaulting to CLI.")
         interface_mode = "cli"

    if interface_mode == "gui":
        try:
            root = tk.Tk()
            app = ScheduleGUI(root, manager)
            def on_closing():
                 if app.check_unsaved_changes():
                      if messagebox.askyesno("Exit Confirmation", "You have unsaved changes. Save before quitting?", parent=root):
                           if not app._save_all_gui(): # Try saving
                                if messagebox.askretrycancel("Save Failed", "Saving failed. Quit anyway (changes will be lost)?", parent=root): root.destroy()
                                return # Don't close if save fails and user cancels retry
                           # If save successful, fall through to destroy
                      else: # User chose not to save
                          if not messagebox.askokcancel("Quit Without Saving?", "Are you sure? Unsaved changes will be lost.", parent=root): return # Don't close if user cancels
                 root.destroy() # Close if no changes, save successful, or quit without saving confirmed

            root.protocol("WM_DELETE_WINDOW", on_closing)
            app.run()
        except tk.TclError as e:
             print(f"{Color.RED}Error initializing GUI: {e}{Color.NC}")
             print("Ensure graphical environment and Tkinter are available. Falling back to CLI.")
             logger.error(f"GUI TclError: {e}", exc_info=True)
             try: run_cli(manager, auto_mode=auto_mode_cli)
             except Exception as cli_fallback_err: logger.error(f"CLI fallback failed: {cli_fallback_err}", exc_info=True); print(f"{Color.RED}CLI fallback failed.{Color.NC}"); sys.exit(1)
        except Exception as e:
             logger.error(f"Unexpected error in GUI mode: {e}", exc_info=True)
             print(f"{Color.RED}Unexpected error: {e}. Check log. Attempting CLI fallback.{Color.NC}")
             try: run_cli(manager, auto_mode=auto_mode_cli)
             except Exception as cli_fallback_err: logger.error(f"CLI fallback failed: {cli_fallback_err}", exc_info=True); print(f"{Color.RED}CLI fallback failed.{Color.NC}"); sys.exit(1)

    else: # Run CLI
        try: run_cli(manager, auto_mode=auto_mode_cli)
        except KeyboardInterrupt: print(f"\n{Color.YELLOW}Operation interrupted. Exiting.{Color.NC}"); sys.exit(0)
        except Exception as e: logger.error(f"Unexpected error in CLI mode: {e}", exc_info=True); print(f"\n{Color.RED}Unexpected error: {e}. Check log.{Color.NC}"); sys.exit(1)