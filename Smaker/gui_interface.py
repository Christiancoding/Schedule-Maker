import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, font as tkFont
from datetime import datetime
from config import *
import logging

logger = logging.getLogger("schedule_maker")
# =============================================================================
# == Graphical User Interface (GUI) Class
# =============================================================================

class PlanEditorDialog(simpledialog.Dialog):
    """Modern dialog for adding/editing a plan with enhanced styling."""
    
    def __init__(self, parent, title="Plan Details", initial_plan=None):
        self.plan = initial_plan if initial_plan else {"name": "", "details": ""}
        super().__init__(parent, title=title)

    def body(self, master):
        # Configure the dialog styling
        master.configure(bg="#ECF0F1")
        
        # Create styled frame
        main_frame = ttk.Frame(master, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="Plan Information",
                               font=("Segoe UI", 14, "bold"),
                               foreground="#2C3E50")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Name field
        ttk.Label(main_frame, 
                 text="Plan Name:",
                 font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        
        self.name_entry = ttk.Entry(main_frame, width=35, font=("Segoe UI", 10))
        self.name_entry.grid(row=1, column=1, sticky="ew", pady=5)

        # Details field
        ttk.Label(main_frame, 
                 text="Details:",
                 font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        
        self.details_entry = ttk.Entry(main_frame, width=35, font=("Segoe UI", 10))
        self.details_entry.grid(row=2, column=1, sticky="ew", pady=5)

        # Help text
        help_label = ttk.Label(main_frame,
                              text="Enter plan name (required) and details like time, location, etc.",
                              font=("Segoe UI", 9),
                              foreground="#7F8C8D")
        help_label.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        # Populate with existing data
        self.name_entry.insert(0, self.plan.get("name", ""))
        self.details_entry.insert(0, self.plan.get("details", ""))

        # Configure column weights
        main_frame.columnconfigure(1, weight=1)

        return self.name_entry  # initial focus

    def apply(self):
        name = self.name_entry.get().strip()
        details = self.details_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Input Error", "Plan name cannot be empty.", parent=self)
            self.result = None
        else:
            self.plan["name"] = name
            self.plan["details"] = details
            self.result = self.plan

    def buttonbox(self):
        """Add custom styled buttons."""
        box = ttk.Frame(self)
        
        # Save button
        save_btn = ttk.Button(box, text="Save", width=10, command=self.ok, default=tk.ACTIVE)
        save_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Cancel button  
        cancel_btn = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        cancel_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        
        box.pack(pady=(10, 0))

class ScheduleGUI:
    """Enhanced Tkinter GUI with modern styling and improved user experience."""

    def __init__(self, root, manager):
        self.root = root
        self.manager = manager
        self.current_day_index = 0

        # Use the DAYS constant from your existing code
        self.DAYS = ["Monday", "Tues", "Wed", "Thur", "Fri", "Sat", "Sun"]

        # GUI Variables
        self.day_vars = {}
        for day in self.DAYS:
            self.day_vars[day] = {
                "study_time": tk.StringVar(),
                "goals": tk.StringVar(),
                "plans": list()
            }

        # Enhanced color scheme
        self.colors = {
            "primary": "#2C3E50",          # Dark blue-gray
            "secondary": "#3498DB",        # Blue
            "accent": "#E74C3C",          # Red
            "success": "#27AE60",         # Green
            "warning": "#F39C12",         # Orange
            "bg_main": "#ECF0F1",         # Light gray
            "bg_card": "#FFFFFF",         # White
            "bg_input": "#FFFFFF",        # White
            "text_primary": "#2C3E50",    # Dark text
            "text_secondary": "#7F8C8D",  # Gray text
            "border": "#BDC3C7",          # Light border
            "hover": "#3498DB",           # Blue hover
            "disabled": "#95A5A6"         # Gray disabled
        }

        # Enhanced fonts
        self.fonts = {
            "title": ("Segoe UI", 20, "bold"),
            "heading": ("Segoe UI", 14, "bold"),
            "subheading": ("Segoe UI", 12, "bold"),
            "body": ("Segoe UI", 10),
            "small": ("Segoe UI", 9),
            "button": ("Segoe UI", 10, "bold")
        }

        self._setup_styles()
        self._setup_ui()
        self._load_data_into_gui()

    def _setup_styles(self):
        """Configure modern ttk styles."""
        self.style = ttk.Style()
        
        # Use a clean theme
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            self.style.theme_use('default')

        # Configure main styles
        self.style.configure(".", 
                           background=self.colors["bg_main"],
                           foreground=self.colors["text_primary"],
                           font=self.fonts["body"])

        # Frame styles
        self.style.configure("Card.TFrame", 
                           background=self.colors["bg_card"],
                           relief="solid",
                           borderwidth=1)

        self.style.configure("Sidebar.TFrame",
                           background=self.colors["primary"])

        # Label styles
        self.style.configure("Title.TLabel",
                           font=self.fonts["title"],
                           background=self.colors["bg_main"],
                           foreground=self.colors["primary"])

        self.style.configure("Heading.TLabel",
                           font=self.fonts["heading"],
                           background=self.colors["bg_card"],
                           foreground=self.colors["primary"])

        self.style.configure("Subheading.TLabel",
                           font=self.fonts["subheading"],
                           background=self.colors["bg_card"],
                           foreground=self.colors["secondary"])

        self.style.configure("SidebarHeading.TLabel",
                           font=self.fonts["heading"],
                           background=self.colors["primary"],
                           foreground="white")

        self.style.configure("StatusBar.TLabel",
                           font=self.fonts["small"],
                           background=self.colors["bg_main"],
                           foreground=self.colors["text_secondary"],
                           relief="sunken",
                           padding=(5, 2))

        # Entry styles
        self.style.configure("Modern.TEntry",
                           fieldbackground=self.colors["bg_input"],
                           borderwidth=2,
                           relief="flat",
                           padding=8)

        self.style.map("Modern.TEntry",
                      focuscolor=[('focus', self.colors["secondary"])])

        # Button styles
        self.style.configure("Primary.TButton",
                           font=self.fonts["button"],
                           background=self.colors["secondary"],
                           foreground="white",
                           borderwidth=0,
                           padding=(15, 8))

        self.style.map("Primary.TButton",
                      background=[('active', self.colors["hover"]),
                                ('pressed', '#2980B9')])

        self.style.configure("Success.TButton",
                           font=self.fonts["button"],
                           background=self.colors["success"],
                           foreground="white",
                           borderwidth=0,
                           padding=(15, 8))

        self.style.map("Success.TButton",
                      background=[('active', '#229954')])

        self.style.configure("Warning.TButton",
                           font=self.fonts["button"],
                           background=self.colors["warning"],
                           foreground="white",
                           borderwidth=0,
                           padding=(15, 8))

        self.style.map("Warning.TButton",
                      background=[('active', '#E67E22')])

        self.style.configure("Danger.TButton",
                           font=self.fonts["button"],
                           background=self.colors["accent"],
                           foreground="white",
                           borderwidth=0,
                           padding=(15, 8))

        self.style.map("Danger.TButton",
                      background=[('active', '#C0392B')])

        self.style.configure("Secondary.TButton",
                           font=self.fonts["button"],
                           background=self.colors["bg_card"],
                           foreground=self.colors["text_primary"],
                           borderwidth=1,
                           relief="solid",
                           padding=(12, 6))

        self.style.map("Secondary.TButton",
                      background=[('active', self.colors["bg_main"])])

        # Notebook styles for day navigation
        self.style.configure("DayTab.TNotebook.Tab",
                           background=self.colors["bg_card"],
                           foreground=self.colors["text_primary"],
                           padding=[15, 8])

        self.style.map("DayTab.TNotebook.Tab",
                      background=[('selected', self.colors["secondary"]),
                                ('active', self.colors["hover"])],
                      foreground=[('selected', 'white')])

    def _setup_ui(self):
        """Create modern UI with improved layout."""
        self.root.title("Schedule Maker - Modern Interface")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg=self.colors["bg_main"])

        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Header
        self._create_header(main_container)

        # Main content area
        content_frame = ttk.Frame(main_container)
        content_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(20, 0))
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # Left sidebar with day navigation
        self._create_sidebar(content_frame)

        # Main content area
        self._create_main_content(content_frame)

        # Status bar
        self._create_status_bar(main_container)

    def _create_header(self, parent):
        """Create the application header."""
        header_frame = ttk.Frame(parent, style="Card.TFrame")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(header_frame, 
                               text="Weekly Schedule Manager",
                               style="Title.TLabel")
        title_label.grid(row=0, column=0, sticky="w", padx=20, pady=15)

        # Current date
        current_date = datetime.now().strftime("%B %d, %Y")
        date_label = ttk.Label(header_frame,
                              text=current_date,
                              font=self.fonts["subheading"],
                              foreground=self.colors["text_secondary"])
        date_label.grid(row=0, column=1, sticky="e", padx=20, pady=15)

    def _create_sidebar(self, parent):
        """Create the left sidebar with day navigation."""
        sidebar_frame = ttk.Frame(parent, style="Sidebar.TFrame")
        sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        sidebar_frame.configure(padding=20)

        # Sidebar title
        sidebar_title = ttk.Label(sidebar_frame,
                                 text="Days",
                                 style="SidebarHeading.TLabel")
        sidebar_title.pack(anchor="w", pady=(0, 20))

        # Day buttons
        self.day_buttons = {}
        
        for i, day in enumerate(self.DAYS):
            btn = tk.Button(sidebar_frame,
                           text=day,
                           font=self.fonts["button"],
                           bg=self.colors["primary"] if i != 0 else self.colors["secondary"],
                           fg="white",
                           bd=0,
                           relief="flat",
                           pady=12,
                           cursor="hand2",
                           command=lambda d=i: self._select_day(d))
            btn.pack(fill="x", pady=2)
            self.day_buttons[i] = btn

        # Quick actions
        ttk.Separator(sidebar_frame, orient="horizontal").pack(fill="x", pady=20)
        
        quick_actions_label = ttk.Label(sidebar_frame,
                                       text="Quick Actions",
                                       style="SidebarHeading.TLabel")
        quick_actions_label.pack(anchor="w", pady=(0, 10))

        # Save button
        save_btn = tk.Button(sidebar_frame,
                            text="💾 Save All",
                            font=self.fonts["button"],
                            bg=self.colors["success"],
                            fg="white",
                            bd=0,
                            relief="flat",
                            pady=8,
                            cursor="hand2",
                            command=self._save_all_gui)
        save_btn.pack(fill="x", pady=2)

        # Generate files button
        generate_btn = tk.Button(sidebar_frame,
                                text="📄 Generate Files",
                                font=self.fonts["button"],
                                bg=self.colors["warning"],
                                fg="white",
                                bd=0,
                                relief="flat",
                                pady=8,
                                cursor="hand2",
                                command=self._generate_files_gui)
        generate_btn.pack(fill="x", pady=2)

        # Send email button
        email_btn = tk.Button(sidebar_frame,
                             text="📧 Send Email",
                             font=self.fonts["button"],
                             bg=self.colors["accent"],
                             fg="white",
                             bd=0,
                             relief="flat",
                             pady=8,
                             cursor="hand2",
                             command=self._send_email_gui)
        email_btn.pack(fill="x", pady=2)

        # Configure email button
        config_btn = tk.Button(sidebar_frame,
                              text="⚙️ Configure",
                              font=self.fonts["button"],
                              bg=self.colors["primary"],
                              fg="white",
                              bd=0,
                              relief="flat",
                              pady=8,
                              cursor="hand2",
                              command=self._configure_email_gui)
        config_btn.pack(fill="x", pady=2)

    def _create_main_content(self, parent):
        """Create the main content area."""
        # Main content frame
        main_content = ttk.Frame(parent, style="Card.TFrame")
        main_content.grid(row=0, column=1, sticky="nsew")
        main_content.columnconfigure(0, weight=1)
        main_content.rowconfigure(1, weight=1)

        # Content header
        content_header = ttk.Frame(main_content)
        content_header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        content_header.columnconfigure(1, weight=1)

        # Current day label
        self.current_day_label = ttk.Label(content_header,
                                          text="Monday Schedule",
                                          style="Heading.TLabel")
        self.current_day_label.grid(row=0, column=0, sticky="w")

        # Content body
        content_body = ttk.Frame(main_content)
        content_body.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        content_body.columnconfigure(1, weight=1)
        content_body.rowconfigure(0, weight=1)

        # Left content (schedule details)
        self._create_schedule_section(content_body)

        # Right content (notes)
        self._create_notes_section(content_body)

    def _create_schedule_section(self, parent):
        """Create the schedule input section."""
        schedule_frame = ttk.Frame(parent)
        schedule_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        schedule_frame.columnconfigure(0, weight=1)

        # Study time section
        study_section = ttk.LabelFrame(schedule_frame, text="📚 Study Time", padding=15)
        study_section.pack(fill="x", pady=(0, 15))
        study_section.columnconfigure(1, weight=1)

        ttk.Label(study_section, text="Time:", font=self.fonts["body"]).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.study_time_entry = ttk.Entry(study_section, 
                                         textvariable=self.day_vars["Monday"]["study_time"],
                                         style="Modern.TEntry",
                                         font=self.fonts["body"])
        self.study_time_entry.grid(row=0, column=1, sticky="ew")

        # Goals section
        goals_section = ttk.LabelFrame(schedule_frame, text="🎯 Study Goals", padding=15)
        goals_section.pack(fill="x", pady=(0, 15))
        goals_section.columnconfigure(1, weight=1)

        ttk.Label(goals_section, text="Goals:", font=self.fonts["body"]).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.goals_entry = ttk.Entry(goals_section,
                                    textvariable=self.day_vars["Monday"]["goals"],
                                    style="Modern.TEntry",
                                    font=self.fonts["body"])
        self.goals_entry.grid(row=0, column=1, sticky="ew")

        # Plans section
        plans_section = ttk.LabelFrame(schedule_frame, text="📋 Plans & Activities", padding=15)
        plans_section.pack(fill="both", expand=True)
        plans_section.columnconfigure(0, weight=1)
        plans_section.rowconfigure(1, weight=1)

        # Plans toolbar
        plans_toolbar = ttk.Frame(plans_section)
        plans_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        add_plan_btn = ttk.Button(plans_toolbar, text="+ Add Plan", 
                                 style="Primary.TButton",
                                 command=self._add_plan_gui)
        add_plan_btn.pack(side="left", padx=(0, 10))

        self.edit_plan_btn = ttk.Button(plans_toolbar, text="✏️ Edit", 
                                       style="Secondary.TButton",
                                       state="disabled",
                                       command=self._edit_plan_gui)
        self.edit_plan_btn.pack(side="left", padx=(0, 10))

        self.remove_plan_btn = ttk.Button(plans_toolbar, text="🗑️ Remove", 
                                         style="Danger.TButton",
                                         state="disabled",
                                         command=self._remove_plan_gui)
        self.remove_plan_btn.pack(side="left")

        # Plans listbox with custom styling
        listbox_frame = ttk.Frame(plans_section)
        listbox_frame.grid(row=1, column=0, sticky="nsew")
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)

        self.plans_listbox = tk.Listbox(listbox_frame,
                                       font=self.fonts["body"],
                                       bg=self.colors["bg_input"],
                                       fg=self.colors["text_primary"],
                                       selectbackground=self.colors["secondary"],
                                       selectforeground="white",
                                       borderwidth=1,
                                       relief="solid",
                                       highlightthickness=0)
        self.plans_listbox.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for listbox
        plans_scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", 
                                       command=self.plans_listbox.yview)
        plans_scrollbar.grid(row=0, column=1, sticky="ns")
        self.plans_listbox.config(yscrollcommand=plans_scrollbar.set)

        # Bind events
        self.plans_listbox.bind("<<ListboxSelect>>", self._on_plan_select)
        self.plans_listbox.bind("<Double-Button-1>", self._edit_plan_gui)

    def _create_notes_section(self, parent):
        """Create the notes section."""
        notes_frame = ttk.LabelFrame(parent, text="📝 Weekly Notes", padding=15)
        notes_frame.grid(row=0, column=1, sticky="nsew")
        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)

        # Notes text area
        self.notes_text = scrolledtext.ScrolledText(notes_frame,
                                                   wrap=tk.WORD,
                                                   font=self.fonts["body"],
                                                   bg=self.colors["bg_input"],
                                                   fg=self.colors["text_primary"],
                                                   borderwidth=1,
                                                   relief="solid",
                                                   highlightthickness=0)
        self.notes_text.grid(row=0, column=0, sticky="nsew")

        self.notes_modified_flag = False
        self.notes_text.bind("<<Modified>>", self._notes_modified_callback)

    def _create_status_bar(self, parent):
        """Create the status bar."""
        self.status_var = tk.StringVar(value="Ready - Schedule Maker with Keyring Support")
        status_bar = ttk.Label(parent, 
                              textvariable=self.status_var,
                              style="StatusBar.TLabel")
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(20, 0))

    def _select_day(self, day_index):
        """Handle day selection from sidebar."""
        # Update button states
        for i, btn in self.day_buttons.items():
            if i == day_index:
                btn.configure(bg=self.colors["secondary"])
            else:
                btn.configure(bg=self.colors["primary"])

        self.current_day_index = day_index
        self._update_day_widgets()

        self.current_day_label.config(text=f"{self.DAYS[day_index]} Schedule")
        self.status_var.set(f"Switched to {self.DAYS[day_index]}")

    # Placeholder methods - these would connect to your existing manager logic
    def _update_day_widgets(self):
        """Update widgets for current day."""
        current_day = self.DAYS[self.current_day_index]
        
        self.study_time_entry.config(textvariable=self.day_vars[current_day]["study_time"])
        self.goals_entry.config(textvariable=self.day_vars[current_day]["goals"])
        self._populate_plans_listbox()


    def _populate_plans_listbox(self):
        """Populate the plans listbox for current day."""
        self.plans_listbox.delete(0, tk.END)
        days = ["Monday", "Tues", "Wed", "Thur", "Fri", "Sat", "Sun"]
        current_day = days[self.current_day_index]
        plans = self.day_vars[current_day].get("plans", [])
        
        for plan in plans:
            display_text = f"{plan.get('name', 'Unnamed')}: {plan.get('details', 'No details')}"
            self.plans_listbox.insert(tk.END, display_text)
        
        self._on_plan_select()

    def _on_plan_select(self, event=None):
        """Handle plan selection."""
        selection = self.plans_listbox.curselection()
        if selection:
            self.edit_plan_btn.config(state="normal")
            self.remove_plan_btn.config(state="normal")
        else:
            self.edit_plan_btn.config(state="disabled")
            self.remove_plan_btn.config(state="disabled")

    def _notes_modified_callback(self, event=None):
        """Handle notes modification."""
        self.notes_modified_flag = True
        try:
            self.notes_text.edit_modified(False)
        except tk.TclError:
            pass

    def _load_data_into_gui(self):
        """Load data from ScheduleManager into the GUI variables and widgets."""
        self.manager.load_credentials(prompt_if_missing=False)
        self.manager.load_schedule_data()
        self.manager.load_notes()

        # Update StringVars and plan lists based on loaded manager schedule
        for day in self.DAYS:
            day_data = self.manager.schedule.get(day, self.manager.initialize_default_schedule()[day])
            self.day_vars[day]["study_time"].set(day_data.get("study_time", ""))
            self.day_vars[day]["goals"].set(day_data.get("goals", ""))
            # Copy the list to avoid modifying manager's data directly until save
            self.day_vars[day]["plans"] = list(day_data.get("plans", []))

        # Load additional notes
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", self.manager.additional_notes)
        self.notes_text.edit_modified(False)
        self.notes_modified_flag = False

        self._update_day_widgets()
        self.status_var.set("Schedule and credential data loaded.")

    # Real implementation methods that integrate with your existing manager
    def _add_plan_gui(self):
        """Handle adding a new plan via dialog."""
        current_day = self.DAYS[self.current_day_index]
        dialog = PlanEditorDialog(self.root, title=f"Add Plan for {current_day}")
        new_plan = dialog.result

        if new_plan and new_plan.get("name"):
            self.day_vars[current_day]["plans"].append(new_plan)
            self._populate_plans_listbox()
            self.status_var.set(f"Added plan '{new_plan['name']}' for {current_day}.")
        elif new_plan is not None:
            self.status_var.set("Add plan cancelled or invalid input.")

    def _edit_plan_gui(self, event=None):
        """Handle editing the selected plan via dialog."""
        selection = self.plans_listbox.curselection()
        if not selection:
            return
        index = selection[0]

        current_day = self.DAYS[self.current_day_index]
        plans = self.day_vars[current_day]["plans"]

        if 0 <= index < len(plans):
            plan_to_edit = plans[index]
            dialog = PlanEditorDialog(self.root, title=f"Edit Plan for {current_day}", 
                                    initial_plan=plan_to_edit.copy())
            updated_plan = dialog.result

            if updated_plan and updated_plan.get("name"):
                self.day_vars[current_day]["plans"][index] = updated_plan
                self._populate_plans_listbox()
                self.plans_listbox.selection_set(index)
                self.status_var.set(f"Updated plan '{updated_plan['name']}' for {current_day}.")
            elif updated_plan is not None:
                self.status_var.set("Edit plan cancelled or invalid input.")

    def _remove_plan_gui(self):
        """Handle removing the selected plan."""
        selection = self.plans_listbox.curselection()
        if not selection:
            return
        index = selection[0]

        current_day = self.DAYS[self.current_day_index]
        plans = self.day_vars[current_day]["plans"]

        if 0 <= index < len(plans):
            removed_plan = plans.pop(index)
            self._populate_plans_listbox()
            self.status_var.set(f"Removed plan '{removed_plan.get('name', 'N/A')}' for {current_day}.")

    def _collect_data_from_gui(self):
        """Collect data from GUI variables into a schedule dictionary."""
        schedule_data = {}
        for day in self.DAYS:
            schedule_data[day] = {
                "study_time": self.day_vars[day]["study_time"].get().strip(),
                "goals": self.day_vars[day]["goals"].get().strip(),
                "plans": list(self.day_vars[day].get("plans", []))
            }
        return schedule_data

    def _is_schedule_modified(self):
        """Check if the schedule data in the GUI differs from the manager's loaded data."""
        gui_schedule = self._collect_data_from_gui()
        if gui_schedule.keys() != self.manager.schedule.keys():
            return True
        for day in self.DAYS:
            mgr_day_data = self.manager.schedule.get(day, {})
            if gui_schedule[day]['study_time'] != mgr_day_data.get('study_time', ''):
                return True
            if gui_schedule[day]['goals'] != mgr_day_data.get('goals', ''):
                return True
            if gui_schedule[day]['plans'] != mgr_day_data.get('plans', []):
                return True
        return False

    def _is_notes_modified(self):
        """Check if the notes text widget content differs from the manager's loaded notes."""
        if self.notes_modified_flag:
            return True
        gui_notes = self.notes_text.get("1.0", tk.END).rstrip('\n')
        mgr_notes = self.manager.additional_notes.rstrip('\n')
        return gui_notes != mgr_notes

    def _save_all_gui(self):
        """Save the current schedule and notes from the GUI."""
        self.status_var.set("Saving...")
        self.root.update_idletasks()

        schedule_data = self._collect_data_from_gui()
        notes_data = self.notes_text.get("1.0", tk.END).strip()

        schedule_saved = self.manager.save_schedule_data(schedule_data)
        notes_saved = self.manager.save_notes(notes_data)

        if schedule_saved and notes_saved:
            self.status_var.set("Schedule and notes saved successfully.")
            self.notes_modified_flag = False
            self.manager.schedule = schedule_data
            self.manager.additional_notes = notes_data
            messagebox.showinfo("Saved", "Schedule and notes saved successfully.", parent=self.root)
            return True
        elif schedule_saved:
            self.status_var.set("Schedule saved, but notes failed.")
            messagebox.showwarning("Partial Save", "Schedule data saved, but failed to save additional notes.", parent=self.root)
            return False
        elif notes_saved:
            self.status_var.set("Notes saved, but schedule failed.")
            messagebox.showwarning("Partial Save", "Additional notes saved, but failed to save schedule data.", parent=self.root)
            self.notes_modified_flag = False
            self.manager.additional_notes = notes_data
            return False
        else:
            self.status_var.set("Error: Failed to save schedule and notes.")
            messagebox.showerror("Save Error", "Failed to save schedule data and additional notes.", parent=self.root)
            return False

    def _generate_files_gui(self):
        """Generate output files (TXT, HTML) from GUI data."""
        if self._is_schedule_modified() or self._is_notes_modified():
            if messagebox.askyesno("Save Before Generating?", 
                                 "You have unsaved changes. Save before generating files?", 
                                 parent=self.root):
                if not self._save_all_gui():
                    messagebox.showerror("Generate Error", 
                                       "Cannot generate files because saving failed.", 
                                       parent=self.root)
                    return False
            else:
                messagebox.showwarning("Generate Cancelled", 
                                     "File generation cancelled. Please save changes first.", 
                                     parent=self.root)
                return False

        self.status_var.set("Generating files...")
        self.root.update_idletasks()
        
        saved_files = self.manager.save_generated_files()

        if saved_files:
            from pathlib import Path
            file_list = "\n".join([f"- {Path(p).name} (in {Path(p).parent.name})" 
                                 for p in saved_files.values()])
            self.status_var.set("Output files generated.")
            messagebox.showinfo("Files Generated", f"Generated files:\n{file_list}", 
                              parent=self.root)
            return True
        else:
            self.status_var.set("Error generating files.")
            messagebox.showerror("Generate Error", "Failed to generate output files.", 
                               parent=self.root)
            return False

    def _send_email_gui(self):
        """Send the schedule email from the GUI using keyring."""
        if self._is_schedule_modified() or self._is_notes_modified():
            if messagebox.askyesno("Save & Generate Before Sending?", 
                                 "You have unsaved changes. Save and generate files before sending email?", 
                                 parent=self.root):
                if not self._save_all_gui():
                    messagebox.showerror("Email Error", 
                                       "Cannot send email because saving failed.", 
                                       parent=self.root)
                    return
                if not self._generate_files_gui():
                    messagebox.showerror("Email Error", 
                                       "Cannot send email because file generation failed after saving.", 
                                       parent=self.root)
                    return
            else:
                messagebox.showwarning("Email Cancelled", 
                                     "Email sending cancelled. Please save changes and generate files first.", 
                                     parent=self.root)
                return
        else:
            if not self._generate_files_gui():
                messagebox.showerror("Email Error", 
                                   "Cannot send email because file generation failed.", 
                                   parent=self.root)
                return

        creds = self.manager.credentials
        missing_creds = [k for k in ['email_to', 'email_from', 'smtp_user', 'smtp_server'] 
                        if not creds.get(k)]
        if missing_creds:
            missing_str = ", ".join([m.replace('_',' ').title() for m in missing_creds])
            if messagebox.askyesno("Configure Email?", 
                                 f"Email configuration incomplete ({missing_str}). Configure now?", 
                                 parent=self.root):
                self._configure_email_gui()
                creds = self.manager.credentials
                missing_creds = [k for k in ['email_to', 'email_from', 'smtp_user', 'smtp_server'] 
                               if not creds.get(k)]
                if missing_creds:
                    messagebox.showerror("Email Error", 
                                       "Email configuration still incomplete. Cannot send email.", 
                                       parent=self.root)
                    return
            else:
                messagebox.showwarning("Email Skipped", "Email sending cancelled.", 
                                     parent=self.root)
                return

        self.status_var.set("Sending email...")
        self.root.update_idletasks()
        success, message = self.manager.send_email_with_attachments()
        self.status_var.set(message)
        
        if success:
            messagebox.showinfo("Email Sent", message, parent=self.root)
        else:
            if "not found in keyring" in message or "Authentication Failed" in message:
                if messagebox.askyesno("Password Missing/Incorrect", 
                                     f"{message}\n\nConfigure email settings (including password) now?", 
                                     parent=self.root):
                    self._configure_email_gui()
                else:
                    messagebox.showerror("Email Error", message, parent=self.root)
            else:
                messagebox.showerror("Email Error", message, parent=self.root)

    def _configure_email_gui(self):
        """Open the email configuration dialog."""
        self.status_var.set("Configuring email...")
        self.manager._prompt_credentials_gui(self.root)
        self.status_var.set("Email configuration closed.")

    def check_unsaved_changes(self):
        """Checks if there are unsaved schedule or notes changes."""
        return self._is_schedule_modified() or self._is_notes_modified()

    def run(self):
        """Start the GUI."""
        self.root.mainloop()