import requests
import pyperclip
import time
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import tkinter.messagebox as msgbox
import pygetwindow as gw
import pystray
from PIL import Image, ImageDraw
import sys
import ctypes
from ctypes import wintypes
import concurrent.futures
import winsound
import queue
import os
import json
import webbrowser
import keyboard

# -------------------- App Version --------------------
APP_VERSION = "0.0.1"  # desktop helper version
# -----------------------------------------------------

MIN_ADDON_VERSION = "0.0.1"
MAX_ADDON_VERSION = "0.0.999"

APP_NAME = "ArmorySpy Desktop App"
config_dir = os.path.join(os.getenv("APPDATA") or ".", APP_NAME)
os.makedirs(config_dir, exist_ok=True)
config_path = os.path.join(config_dir, "config.json")

# -------------------- Config Persistence --------------------
def save_config(vk, mods):
    with open(config_path, "w") as f:
        json.dump({"hotkey_vk": vk, "hotkey_mods": mods}, f)

def load_config():
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            vk = data.get("hotkey_vk")
            mods = data.get("hotkey_mods", 0)
            return vk, mods
    except FileNotFoundError:
        return None, 0

 # -------------------- Check for updates --------------------   
GITHUB_API_URL = "https://api.github.com/repos/ASpyDef/AromorySpy-Desktop-App/releases/latest"

def show_update_popup(latest_version, current_version):
    root = tk.Toplevel()
    root.title("Update Available")
    root.geometry("400x150")
    root.attributes("-topmost", True)

    msg = f"New version available: {latest_version}\nYou are on: {current_version}"
    tk.Label(root, text=msg, font=("Arial", 10), justify="center").pack(pady=10)

    link_url = "https://github.com/ASpyDef/AromorySpy-Desktop-App"
    link_label = tk.Label(root, text=link_url, font=("Arial", 10, "underline"), fg="blue", cursor="hand2")
    link_label.pack(pady=10)
    link_label.bind("<Button-1>", lambda e: webbrowser.open(link_url))

    tk.Button(root, text="Close", command=root.destroy).pack(pady=5)

def check_for_update(current_version):
    def worker():
        try:
            r = requests.get(GITHUB_API_URL, timeout=5)
            r.raise_for_status()
            latest_release = r.json()
            latest_version = latest_release["tag_name"].lstrip("v")

            if latest_version != current_version:
                print(f"New version available: {latest_version} (You are on: {current_version})")
                # schedule popup in main Tkinter loop
                root = tk._default_root
                if root:
                    root.after(0, lambda: show_update_popup(latest_version, current_version))
            else:
                print(f"App version is up to date: {current_version}")

        except Exception as e:
            print("Failed to check for updates:", e)

    threading.Thread(target=worker, daemon=True).start()
    
# -------------------- Version check --------------------
def is_version_compatible(addon_version, min_version, max_version=None):
    try:
        av = [int(x) for x in addon_version.split(".")]
        mv = [int(x) for x in min_version.split(".")]

        # pad shorter version with zeros
        while len(av) < len(mv): av.append(0)
        while len(mv) < len(av): mv.append(0)

        if av < mv:
            return False

        if max_version:
            xv = [int(x) for x in max_version.split(".")]
            while len(av) < len(xv): av.append(0)
            while len(xv) < len(av): xv.append(0)
            if av > xv:
                return False

        return True
    except Exception as e:
        print("Invalid addon version format:", addon_version)
        return False
    
def show_version_warning(addon_version, min_version, max_version):
    msg = f"Addon version {addon_version} is not supported.\n" \
          f"Supported range: {min_version} – {max_version}\n\n" \
          "The data structure may be incompatible."
    # popup will stay on top even if console is hidden
    root.after(0, lambda: msgbox.showwarning("Unsupported Addon Version", msg))

# -------------------- Windows Hotkey Setup --------------------
user32 = ctypes.windll.user32
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 1

NAV_KEYS = {
    0x70:"F1",0x71:"F2",0x72:"F3",0x73:"F4",
    0x74:"F5",0x75:"F6",0x76:"F7",0x77:"F8",
    0x78:"F9",0x79:"F10",0x7A:"F11",0x7B:"F12",
    0x21:"PageUp",0x22:"PageDown",
}

current_hotkey_vk, current_modifiers = load_config()
if current_hotkey_vk is None:
    current_hotkey_vk = None  # default is no hotkey
    current_modifiers = 0

app_paused = False
lookup_running = False
root = tk.Tk()
root.withdraw()

spinner = None
console_window = None

API_URL = "https://classic-armory.org/api/v1/character"
FLAVOR = "tbc-anniversary"
HEADERS = {"User-Agent":"Mozilla/5.0","Content-Type":"application/json"}

# -------------------- Console Redirect --------------------
class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.lock = threading.Lock()
    def write(self, message):
        if not message.strip(): return
        if not message.endswith("\n"): message += "\n"
        with self.lock:
            self.text_widget.configure(state="normal")
            self.text_widget.insert(tk.END,message)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state="disabled")
    def flush(self): pass

def create_console_window():
    global console_window, APP_VERSION
    if console_window: return
    console_window = tk.Toplevel(root)
    console_window.title("ArmorySpy Desktop App Console")
    console_window.geometry("600x300")
    console_window.protocol("WM_DELETE_WINDOW", lambda: console_window.withdraw())
    text_area = ScrolledText(console_window, state="disabled", font=("Consolas",10), bg="black", fg="white")
    text_area.pack(fill=tk.BOTH, expand=True)
    sys.stdout = ConsoleRedirector(text_area)
    sys.stderr = ConsoleRedirector(text_area)
    print("ArmorySpy Desktop App running")
    print("AppVersion: ", APP_VERSION)
    console_window.withdraw()

# -------------------- Spinner Overlay --------------------
class SpinnerOverlay:
    def __init__(self, root):
        self.root = root
        self.symbols = ["⏳","⌛"]
        self.index = 0
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.85)
        self.win.configure(bg="black")
        self.label = tk.Label(self.win, text=self.symbols[0], font=("Arial",32), bg="black", fg="white")
        self.label.pack(padx=20, pady=20)
        self.win.withdraw()
        self.running = False
    def update_symbol(self):
        if not self.running: return
        self.index = (self.index+1) % len(self.symbols)
        self.label.config(text=self.symbols[self.index])
        self.win.after(300, self.update_symbol)
    def show(self):
        self.win.update_idletasks()
        w, h = self.win.winfo_width(), self.win.winfo_height()
        ws, hs = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        x, y = (ws//2)-(w//2), (hs//2)-(h//2)
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.deiconify()
        if not self.running:
            self.running = True
            self.update_symbol()
    def hide(self):
        self.running = False
        self.win.withdraw()

spinner = SpinnerOverlay(root)

# -------------------- WoW Focus --------------------
def wow_is_focused():
    win = gw.getActiveWindow()
    if not win:
        return False
    return win.title.strip() == "World of Warcraft"

def focus_wow():
    try:
        windows = [w for w in gw.getWindowsWithTitle("World of Warcraft") if w.title.strip() == "World of Warcraft"]
        if windows:
            win = windows[0]
            win.activate()
            time.sleep(0.15)
            return True
        print("WoW window not found")
        return False
    except Exception as e:
        print("Could not focus WoW window:", e)
        return False

# -------------------- Hotkey System --------------------
hotkey_queue = queue.Queue()

def get_pressed_modifiers():
    mods = 0
    if user32.GetAsyncKeyState(0x10) & 0x8000: mods |= MOD_SHIFT
    if user32.GetAsyncKeyState(0x11) & 0x8000: mods |= MOD_CONTROL
    if user32.GetAsyncKeyState(0x12) & 0x8000: mods |= MOD_ALT
    return mods

def on_hotkey_pressed():
    print("Hotkey triggered")
    if wow_is_focused():
        run_lookup_with_spinner()
    else:
        print("WoW is not in focus")

def hotkey_thread():
    """Dedicated thread to register hotkeys and process WM_HOTKEY messages."""
    global current_hotkey_vk, current_modifiers

    thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
    print("Hotkey thread ID:", thread_id)

    # Register initial hotkey
    if current_hotkey_vk is not None:
        user32.RegisterHotKey(None, HOTKEY_ID, current_modifiers | MOD_NOREPEAT, current_hotkey_vk)
    name = NAV_KEYS.get(current_hotkey_vk, f"VK{current_hotkey_vk}")
    print(f"Initial hotkey registered in thread {thread_id}: {name}")

    msg = wintypes.MSG()

    while True:
        # Process queued hotkey changes
        try:
            while True:  # process all queued changes
                new_vk, new_mods = hotkey_queue.get_nowait()
                user32.UnregisterHotKey(None, HOTKEY_ID)
                if new_vk is not None:
                    success = user32.RegisterHotKey(None, HOTKEY_ID, new_mods | MOD_NOREPEAT, new_vk)
                else:
                    success = True  # clearing hotkey is "successful" by definition
                if success:
                    current_hotkey_vk, current_modifiers = new_vk, new_mods
                    save_config(current_hotkey_vk, current_modifiers)
                    mods_list = []
                    if new_mods & MOD_CONTROL: mods_list.append("Ctrl")
                    if new_mods & MOD_SHIFT: mods_list.append("Shift")
                    if new_mods & MOD_ALT: mods_list.append("Alt")
                    combo = "+".join(mods_list + [NAV_KEYS.get(new_vk, f"VK{new_vk}")])
                    print(f"Hotkey re-registered in thread {thread_id}: {combo}")
                else:
                    err = ctypes.GetLastError()
                    print(f"Failed to register hotkey (keeping previous). Error code: {err}")
        except queue.Empty:
            pass

        # Non-blocking check for messages
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            if current_hotkey_vk is not None and msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                root.after(0, on_hotkey_pressed)
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        time.sleep(0.01)  # small sleep to prevent 100% CPU

def register_hotkey(vk, modifiers):
    hotkey_queue.put((vk, modifiers))

def capture_hotkey_window():
    top = tk.Toplevel(root)
    top.title("Set Hotkey")
    top.geometry("320x250")  # slightly taller for the button

    # Format hotkey string
    def format_hotkey(vk, mods):
        mods_list = []
        if mods & MOD_CONTROL: mods_list.append("Ctrl")
        if mods & MOD_SHIFT: mods_list.append("Shift")
        if mods & MOD_ALT: mods_list.append("Alt")
        return "+".join(mods_list + [NAV_KEYS.get(vk, f"VK{vk}")]) if vk else "None"

    # --- Current Hotkey label ---
    label = tk.Label(
        top,
        text=f"Current Hotkey: {format_hotkey(current_hotkey_vk, current_modifiers)}",
        font=("Arial", 10)
    )
    label.pack(pady=5)

    # --- Text widget for instructions ---
    text_widget = tk.Text(
        top,
        height=10,
        width=60,
        font=("Arial", 10),
        wrap="word",
        bd=0,
        bg=top.cget("bg")
    )
    text_widget.pack(pady=5, padx=5, fill="x")

    # Create a tag for centered text
    text_widget.tag_configure("center", justify="center")
    text_widget.tag_configure("warning", foreground="red", font=("Arial", 10, "bold"), justify="center")

    # Normal instruction line
    text_widget.insert("end", "Press the key combination you want to set...\n\n", "center")

    # Warning line (red and bold)
    text_widget.insert(
        "end",
        "Hotkey is global and reserved while the app is running. "
        "It will not pass through to other applications.\n\n",
        "warning"
    )

    # Allowed keys info (normal)
    text_widget.insert(
        "end",
        "Allowed keys:\n"
        "Function keys (F1-F12) and PageUp, PageDown\n"
        "Modifiers allowed: Ctrl, Shift, Alt\n",
        "center"
    )

    # Make read-only
    text_widget.configure(state="disabled")

    # -------------------- Clear Hotkey Button --------------------
    def clear_hotkey():
        register_hotkey(None, 0)
        label.config(text="Current Hotkey: None")
        print("Hotkey cleared")

    tk.Button(top, text="Clear Hotkey", command=clear_hotkey).pack(pady=5)

    # -------------------- Poll for new hotkey --------------------
    def poll_hotkey():
        for vk in NAV_KEYS:
            if user32.GetAsyncKeyState(vk) & 0x8000:
                mods = get_pressed_modifiers()
                register_hotkey(vk, mods)
                # Update label immediately to reflect new hotkey
                label.config(text=f"Current Hotkey: {format_hotkey(vk, mods)}")
                top.destroy()
                return
        top.after(10, poll_hotkey)

    top.attributes("-topmost", True)
    top.focus_force()
    top.grab_set()
    top.after(10, poll_hotkey)

# -------------------- Clipboard Monitor --------------------
_last_clipboard = None
_ignore_clipboard = False
clipboard_lock = threading.Lock()

def safe_clipboard_paste(retries=3):
    for _ in range(retries):
        try:
            return pyperclip.paste()
        except pyperclip.PyperclipException:
            time.sleep(0.1)
    return None

def clipboard_monitor_loop():
    global _last_clipboard, lookup_running, _ignore_clipboard

    while True:

        current = safe_clipboard_paste()

        if current is None:
            time.sleep(0.4)
            continue

        current = current.strip()

        focused = wow_is_focused() and not app_paused

        with clipboard_lock:

            if focused:

                if _last_clipboard is None:
                    _last_clipboard = current

                elif current and current != _last_clipboard:

                    if not lookup_running and not _ignore_clipboard:
                        _last_clipboard = current
                        root.after(0, run_lookup_with_spinner)
                    else:
                        _last_clipboard = current

            else:
                _last_clipboard = current

        time.sleep(0.4)

def start_clipboard_monitor():
    threading.Thread(target=clipboard_monitor_loop, daemon=True).start()

# -------------------- Lookup (OLD WORKING VERSION) --------------------
def parse_export(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    addon_version = region = realm = None
    names = []
    for line in lines:
        if line.startswith("Addonversion="):
            addon_version = line.split("=", 1)[1].strip()
        elif line.startswith("Region="):
            region = line.split("=", 1)[1].strip()
        elif line.startswith("Realm="):
            realm = line.split("=", 1)[1].strip()
        else:
            names.append(line)
    return addon_version, region, realm, names

def validate_export(addon_version, region, realm, names):
    if not addon_version: 
        print("Invalid export: missing Addonversion")
        return False
    if not region: 
        print("Invalid export: missing Region")
        return False
    if not realm: 
        print("Invalid export: missing Realm")
        return False
    if not names: 
        print("Invalid export: no player names found")
        return False
    return True

def get_gearscore(name, realm, region):
    payload = {"name": name, "realm": realm, "region": region, "flavor": FLAVOR}
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)
        return r.json()["character"]["gearscore"]
    except Exception as e:
        print("API error for", name, e)
        return "0"

def process_names(names, realm, region):
    #spinner.show()
    #root.after(0, spinner.show)
    max_workers = min(20, len(names))
    print("running workers;", max_workers, "of 20")
    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(get_gearscore, name, realm, region): name for name in names}
            for future in concurrent.futures.as_completed(future_map):
                name = future_map[future]
                try: gs = future.result()
                except: gs = "0"
                results.append(f"{name}={gs}")
    finally:
        #spinner.hide()
        #root.after(0, spinner.hide)
        pass
    return "\n".join(results)

def wait_for_modifiers_release():
    # Wait until Shift, Ctrl, Alt are released
    while (user32.GetAsyncKeyState(0x10) & 0x8000 or  # Shift
           user32.GetAsyncKeyState(0x11) & 0x8000 or  # Ctrl
           user32.GetAsyncKeyState(0x12) & 0x8000):   # Alt
        time.sleep(0.01)  # small sleep, responsive

def run_lookup():
    global lookup_running, _last_clipboard, _ignore_clipboard, MIN_ADDON_VERSION, MAX_ADDON_VERSION, APP_VERSION
    if lookup_running or app_paused:
        return
    lookup_running = True
    try:
        if not wow_is_focused(): 
            print("WoW must be focused")
            return

        wait_for_modifiers_release()

        # --- save user's clipboard ---
        try:
            original_clipboard = pyperclip.paste()
        except:
            original_clipboard = ""

        # Copy from WoW
        keyboard.send("ctrl+c")
        time.sleep(0.2)
        try:
            text = pyperclip.paste()
        except:
            print("Clipboard error")
            text = ""

        if not text.strip(): 
            print("Clipboard empty")
            return

        # --- parse export ---
        addon_version, region, realm, names = parse_export(text)

        # validate export
        if not validate_export(addon_version, region, realm, names):
            return

        # check addon version
        if not is_version_compatible(addon_version, MIN_ADDON_VERSION, MAX_ADDON_VERSION):
            print(f"Addon version {addon_version} is not supported. Supported range: {MIN_ADDON_VERSION} – {MAX_ADDON_VERSION}")
            show_version_warning(addon_version, MIN_ADDON_VERSION, MAX_ADDON_VERSION)
            return

        print("Players:", names)

        # --- process names with timing ---
        start_time = time.perf_counter()
        result = process_names(names, realm, region)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f"Lookup completed in {elapsed:.2f} seconds")

        # --- append desktop helper version ---
        result_with_version = f"Appversion={APP_VERSION}\n{result}"

        # --- paste result back into WoW ---
        if focus_wow():
            with clipboard_lock:
                _ignore_clipboard = True
            try:
                pyperclip.copy(result_with_version)
                time.sleep(0.1)
                keyboard.send("ctrl+v")
                winsound.Beep(1000,150)
                time.sleep(0.1)
            finally:
                with clipboard_lock:
                    _ignore_clipboard = False

        # --- restore user's clipboard ---
        with clipboard_lock:
            _ignore_clipboard = True
        try:
            pyperclip.copy(original_clipboard)
            _last_clipboard = original_clipboard.strip()
        finally:
            with clipboard_lock:
                _ignore_clipboard = False

    finally:
        lookup_running = False

def run_lookup_with_spinner():
    root.after(0, spinner.show)
    def task():
        run_lookup()
        root.after(0, spinner.hide)
    threading.Thread(target=task, daemon=True).start()

# -------------------- Tray & GUI --------------------
def create_image(paused=False):
    img = Image.new("RGB", (64,64), "red" if paused else "black")
    d = ImageDraw.Draw(img)
    d.rectangle([16,16,48,48], fill="white" if not paused else "yellow")
    return img

def toggle_pause(icon):
    global app_paused
    app_paused = not app_paused
    icon.icon = create_image(paused=app_paused)
    print("Paused" if app_paused else "Resumed")

def toggle_console(icon=None):
    global console_window
    if console_window is None: create_console_window()
    if console_window.state() != "withdrawn": console_window.withdraw()
    else: console_window.deiconify(); console_window.lift()

def on_exit(icon):
    user32.UnregisterHotKey(None,HOTKEY_ID)
    icon.visible = False
    icon.stop()
    time.sleep(0.05)
    root.destroy()

def setup_tray():
    menu = pystray.Menu(
        pystray.MenuItem("Set Hotkey", lambda icon: capture_hotkey_window()),
        pystray.MenuItem(lambda item: "Resume" if app_paused else "Pause", toggle_pause),
        pystray.MenuItem("Toggle Console", toggle_console),
        pystray.MenuItem("Exit", on_exit)
    )
    tray_icon = pystray.Icon("ArmorySpy Desktop App", create_image(), "ArmorySpy Desktop App", menu)
    threading.Thread(target=tray_icon.run_detached, daemon=True).start()

# -------------------- Main --------------------
def main():
    global APP_VERSION
    print("ArmorySpy Desktop App running")
    print("AppVersion: ", APP_VERSION)
    check_for_update(APP_VERSION)
    create_console_window()
    start_clipboard_monitor()
    setup_tray()
    register_hotkey(current_hotkey_vk, current_modifiers)
    threading.Thread(target=hotkey_thread, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()