# ArmorySpy Desktop App

**Version:** Beta (v0.0.1)  
**Platform:** Windows  

ArmorySpy Desktop App receives character names from the ArmorySpy WoW Addon, looks up GearScore for each character, and pastes the information back into World of Warcraft automatically.

---

## Features

- Lookup GearScore for WoW Classic/Anniversary characters  
- Automatically import GearScore into the ArmorySpy WoW Addon  
- Clipboard tracking when the WoW window is focused  
- Configurable global hotkey for copy/paste actions  
- Tray icon interface for easy control and settings  

---
## Installation

1. Download the latest release `.zip` from GitHub via the green **Code** button in the top right.  
2. Extract the `.exe` or `.py` file.  
3. Run the program:  
   - `.exe`: Double-click to start  
   - `.py`: Run with Python (`python "ArmorySpy Desktop App.py"`)  

---

## Requirements

- **ArmorySpy WoW Addon:** Must be installed in your WoW client  
- **To run the `.exe`:** No additional requirements  
- **To run the `.py` script directly:** Python 3.x
   install required libraries:

```bash
pip install requests pyperclip pygetwindow pystray pillow keyboard
```
---

## Usage

- The app runs in the background as a tray icon.  
- **Right-click the tray icon** to access options:  
  - Set or clear hotkey  
  - Pause/resume clipboard monitoring  
  - Open the console for logs  
  - Exit the app  
- Use the ArmorySpy WoW Addon in-game and follow its instructions for exporting/importing GearScore.  

---

## Notes

- This is a **beta version**. Features may change and improvements will be added over time.  
- The app is safe and only interacts with your clipboard and WoW window; it does **not** collect personal information.  
- The CurseForge link for the ArmorySpy WoW Addon will be added in a future update.  

---

## Contributing

Pull requests, bug reports, and feature suggestions are welcome! Please follow standard GitHub practices for issues and PRs.
