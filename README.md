# Schedule Maker

A comprehensive weekly schedule management application with both command-line and graphical interfaces. Create, manage, and share your weekly schedules with integrated email functionality and secure credential storage.

## Features

### 🗓️ Schedule Management
- **Weekly Planning**: Organize study times, goals, and activities for each day
- **Flexible Plans**: Add multiple plans per day with names and details
- **Goal Setting**: Set specific study goals for each day
- **Additional Notes**: Include weekly notes and reminders

### 🖥️ Dual Interface Options
- **Command Line Interface (CLI)**: Fast, keyboard-driven workflow
- **Graphical User Interface (GUI)**: Modern Tkinter-based interface with intuitive design
- **Auto Mode**: Automated processing for scheduled runs

### 📧 Email Integration
- **HTML Email Generation**: Beautiful, responsive email layouts
- **File Attachments**: Automatically attach schedule files
- **Secure Authentication**: Password storage using system keyring
- **Multiple Format Output**: Text, HTML, and reminder formats

### 🔒 Security & Storage
- **Secure Password Storage**: Uses system keyring for email credentials
- **Data Persistence**: Reliable file-based storage with backup functionality
- **Input Sanitization**: Protection against malicious input
- **Legacy Support**: Backwards compatible with older data formats

## Installation

### Prerequisites
- Python 3.7+
- Tkinter (usually included with Python)

### Required Dependencies
```bash
pip install keyring css-inline
```

### Optional Dependencies
For enhanced functionality:
- `mail` command (for backup email sending on Unix systems)

### Quick Setup
1. Clone or download the application files
2. Install dependencies: `pip install keyring css-inline`
3. Run: `python main.py`

## Usage

### Starting the Application

#### Interactive Mode (Default)
```bash
python main.py
```
The application will prompt you to choose between CLI or GUI interface.

#### Force Specific Interface
```bash
# Command Line Interface
python main.py -cli

# Graphical User Interface  
python main.py -gui

# Automated CLI (no prompts)
python main.py -auto
```

### First Run Setup

1. **Choose Interface**: Select CLI or GUI when prompted
2. **Configure Email** (optional): Set up SMTP settings for email notifications
   - Recipient email address
   - Sender email and SMTP server details
   - Password (stored securely in system keyring)
3. **Create Schedule**: Add study times, goals, and plans for each day

### CLI Interface

The command-line interface provides a step-by-step workflow:

1. **Day-by-Day Entry**: Configure each day of the week
   - Set study times (e.g., "11:00-3:00")
   - Define study goals
   - Add multiple plans with names and details

2. **Additional Actions**:
   - `(N)otes` - Add or update weekly notes
   - `(E)mail` - Send schedule via email
   - `(C)onfigure` - Update email settings
   - `(Q)uit` - Exit application

### GUI Interface

The graphical interface features:

- **Day Navigation**: Click day buttons to switch between days
- **Form Fields**: Easy input for study times and goals
- **Plan Management**: Add, edit, and remove plans with dialog boxes
- **Notes Section**: Rich text area for additional notes
- **Quick Actions**: Save, generate files, send email, and configure settings

## Configuration

### File Locations

All configuration and data files are stored in `~/.schedule_config/`:

```
~/.schedule_config/
├── config.sh              # Legacy configuration (read-only)
├── credentials.ini         # Email settings (non-sensitive)
├── schedule_notes.txt      # Additional weekly notes
├── schedule_email.html     # Generated HTML email
├── Schedules/
│   ├── schedule.txt        # Formatted text schedule
│   └── schedule_reminders.txt
└── PA/
    └── previous_answers.sh # Schedule data storage
```

### Email Configuration

Configure email settings through either interface:

**Required Settings:**
- **Recipient Email**: Where to send the schedule
- **Sender Email**: Your email address
- **SMTP Server**: Email server (e.g., smtp.gmail.com)
- **SMTP Port**: Usually 587 for TLS
- **Username**: SMTP login username
- **Password**: Stored securely in system keyring

**Gmail Setup Example:**
- SMTP Server: `smtp.gmail.com`
- Port: `587`
- Username: Your Gmail address
- Password: App-specific password (recommended)

## Data Format

### Schedule Storage
Schedules are stored in shell script format with JSON-encoded plans:

```bash
schedule[Monday]="11:00-3:00|Study calculus||PLANS||[{\"name\":\"Work\",\"details\":\"Dollar General 2-6pm\"}]"
```

### Legacy Support
The application automatically converts old format data:
- Work schedules → Plan entries
- Day notes → Plan entries
- Goals migration

## Generated Files

The application generates multiple output formats:

1. **schedule.txt**: Beautifully formatted plain text with Unicode borders
2. **schedule_reminders.txt**: Categorized reminders and goals
3. **schedule_email.html**: Responsive HTML email with CSS inlining

## Email Features

### HTML Email Generation
- **Responsive Design**: Mobile-friendly layout
- **Color-Coded Days**: Each day has a unique color theme
- **Structured Content**: Organized sections for study time, goals, and plans
- **Email Client Compatibility**: Tested with Gmail, Outlook, and others

### Backup Email Methods
If SMTP fails, the application attempts to use the system `mail` command as a fallback.

## Troubleshooting

### Common Issues

**GUI Won't Start**:
- Ensure Tkinter is installed: `python -m tkinter`
- Try CLI mode: `python main.py -cli`

**Email Sending Fails**:
- Check SMTP settings in configuration
- Verify password in system keyring
- Test with backup mail command

**Permission Errors**:
- Ensure write access to `~/.schedule_config/`
- Check file permissions on config directory

**Keyring Issues**:
- Install keyring backend for your system
- On Linux, consider installing `python-keyring` system package

### Debug Mode
Enable debug logging by setting `DEBUG = True` in `config.py`.

## Advanced Features

### Automated Scheduling
Use `-auto` mode for scheduled runs:
```bash
# In crontab for weekly email
0 9 * * 1 /usr/bin/python3 /path/to/main.py -auto
```

### Custom Study Times
Default study times can be modified in `config.py`:
```python
DEFAULT_STUDY_TIMES = {
    "Monday": "11:00-3:00",
    "Tues": "11:00-3:00",
    # ... customize as needed
}
```

### Plan Categories
The reminder generator automatically categorizes plans:
- 🤯 Work Schedule
- 📬 Appointments  
- 🍽️ Eating Plans
- 📺 YouTube Videos
- 😪 Sleeping
- 🙏 Praying & Worship
- 🛌 Breaks & Relaxation
- 📚 Study Plans
- 🎮 Play Plans
- 📌 Other Activities

## Security Notes

- Passwords are stored using the system keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- Configuration files have restricted permissions (600)
- Input is sanitized to prevent injection attacks
- No sensitive data is stored in plain text

## Contributing

This is a personal schedule management tool. Feel free to fork and modify for your own needs.

## License

Personal use application. Modify and distribute as needed for personal scheduling requirements.

---

**Version**: 6.0  
**Last Updated**: 2025  
**Python Version**: 3.7+