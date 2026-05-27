import os
import sys
import json
import time
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "pillow", "--quiet"])
    import pystray
    from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR    = os.path.dirname(sys.executable)
    MEIPASS_DIR = sys._MEIPASS
else:
    BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
    MEIPASS_DIR = BASE_DIR

CONFIG_PATH = os.path.join(BASE_DIR, "broadcast_tray_config.json")
ICO_PATH    = os.path.join(MEIPASS_DIR, "BroadcastTray.ico")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "broadcast_exe":              "C:\\Program Files\\NVIDIA Corporation\\NVIDIA Broadcast\\NVIDIA Broadcast UI.exe",
    "obs_exe":                    "C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe",
    "obs_working_dir":            "C:\\Program Files\\obs-studio\\bin\\64bit",
    "teams_process":              "ms-teams",
    "broadcast_stop_processes":   ["Broadcast", "NvVirtual", "NvAFX"],
    "obs_stop_processes":         ["obs"],
    "broadcast_init_wait":        5,
    "update_popup_processes":     ["NvBroadcastInstaller", "OTAUtility", "NvBroadcastInstallerOTA"],
    "update_popup_kill_wait":     8,
    "minimize_broadcast":         False,
    "minimize_obs":               False,
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    return None

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------
def ps_where(fragments):
    return " -or ".join([f'$_.Name -like "*{f}*"' for f in fragments])

def is_running(fragments):
    where = ps_where(fragments)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"$p = Get-Process | Where-Object {{ {where} }}; if ($p) {{ 'yes' }} else {{ 'no' }}"],
        capture_output=True, text=True
    )
    return result.stdout.strip().lower() == "yes"

def kill_processes(fragments, graceful=True):
    where = ps_where(fragments)
    if graceful:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Process | Where-Object {{ {where} }} | ForEach-Object {{ $_.CloseMainWindow() | Out-Null }}"],
            capture_output=True
        )
        time.sleep(3)
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-Process | Where-Object {{ {where} }} | Stop-Process -Force -ErrorAction SilentlyContinue"],
        capture_output=True
    )

def minimize_process(fragments):
    """Minimize all windows belonging to matching processes."""
    where = ps_where(fragments)
    script = (
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"$procs = Get-Process | Where-Object {{ {where} }}; "
        f"foreach ($p in $procs) {{ "
        f"  foreach ($h in $p.MainWindowHandle) {{ "
        f"    if ($h -ne 0) {{ "
        f"      [System.Windows.Forms.SendKeys]::SendWait('%{{F9}}'); "
        f"      $sig = '[DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);'; "
        f"      $type = Add-Type -MemberDefinition $sig -Name WinAPI -Namespace Win32 -PassThru; "
        f"      $type::ShowWindow($h, 6) | Out-Null "
        f"    }} "
        f"  }} "
        f"}}"
    )
    # Simpler approach: use ShowWindow via inline C#
    where2 = ps_where(fragments)
    ps = f"""
$code = @'
using System;
using System.Runtime.InteropServices;
public class WinAPI {{
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}}
'@
Add-Type -TypeDefinition $code
$procs = Get-Process | Where-Object {{ {where2} }}
foreach ($p in $procs) {{
    if ($p.MainWindowHandle -ne 0) {{
        [WinAPI]::ShowWindow($p.MainWindowHandle, 6) | Out-Null
    }}
}}
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)

def start_process(exe_path, working_dir=None):
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    kwargs = {"creationflags": flags}
    if working_dir:
        kwargs["cwd"] = working_dir
    subprocess.Popen([exe_path], **kwargs)

# ---------------------------------------------------------------------------
# Start / Stop logic
# ---------------------------------------------------------------------------
def do_start(cfg):
    # Teams check
    teams_proc = [cfg["teams_process"]]
    if is_running(teams_proc):
        answer = messagebox.askyesno(
            "Close Teams?",
            "Teams is currently running and needs to be closed so it can\n"
            "detect the OBS Virtual Camera when you reopen it.\n\n"
            "Close Teams now?",
            icon="question"
        )
        if answer:
            kill_processes(teams_proc)

    # Start Broadcast (only if not already running)
    if is_running(cfg.get("broadcast_stop_processes", ["Broadcast"])):
        print("Broadcast already running, skipping launch.")
    else:
        start_process(cfg["broadcast_exe"])

    # Wait for Broadcast to initialize
    init_wait = cfg.get("broadcast_init_wait", 5)
    time.sleep(init_wait)

    # Kill update popup - wait a configurable amount then kill
    popup_wait = cfg.get("update_popup_kill_wait", 8)
    popup_procs = cfg.get("update_popup_processes", ["NvBroadcastInstaller", "OTAUtility"])
    time.sleep(popup_wait)
    kill_processes(popup_procs, graceful=False)

    # Minimize Broadcast if configured
    if cfg.get("minimize_broadcast", False):
        time.sleep(1)
        minimize_process(["Broadcast"])

    # Start OBS (only if not already running)
    if is_running(cfg.get("obs_stop_processes", ["obs"])):
        print("OBS already running, skipping launch.")
    else:
        start_process(cfg["obs_exe"], working_dir=cfg.get("obs_working_dir"))

    # Minimize OBS if configured
    if cfg.get("minimize_obs", False):
        time.sleep(3)  # Give OBS time to open before minimizing
        minimize_process(["obs"])

    messagebox.showinfo(
        "Broadcast Started",
        "NVIDIA Broadcast and OBS are running.\n\n"
        "Please open Teams and select 'OBS Virtual Camera'\n"
        "under Settings > Devices > Camera."
    )

def do_stop(cfg):
    kill_processes(cfg["obs_stop_processes"])
    kill_processes(cfg["broadcast_stop_processes"])

# ---------------------------------------------------------------------------
# Tray icon
# ---------------------------------------------------------------------------
def make_icon(active=False):
    if os.path.exists(ICO_PATH):
        try:
            img = Image.open(ICO_PATH).convert("RGBA").resize((64, 64), Image.LANCZOS).copy()
            if active:
                overlay = Image.new("RGBA", img.size, (0, 200, 80, 60))
                img = Image.alpha_composite(img, overlay)
            return img
        except Exception:
            pass

    size  = 64
    img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    color = (0, 200, 80) if active else (160, 160, 160)
    draw.ellipse([4, 4, size-4, size-4], fill=color, outline=(255, 255, 255), width=3)
    if active:
        draw.rectangle([22, 22, 42, 42], fill=(255, 255, 255))
    else:
        draw.polygon([(20, 16), (20, 48), (48, 32)], fill=(255, 255, 255))
    return img

# ---------------------------------------------------------------------------
# Settings window
# ---------------------------------------------------------------------------
def open_settings(cfg, on_save=None):
    win = tk.Tk()
    win.title("Broadcast Tray - Settings")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    pad = {"padx": 8, "pady": 4}

    simple_fields = [
        ("broadcast_exe",          "NVIDIA Broadcast EXE",                   "file"),
        ("obs_exe",                "OBS EXE",                                "file"),
        ("obs_working_dir",        "OBS Working Directory",                  "dir"),
        ("teams_process",          "Teams Process Name",                     "text"),
        ("broadcast_init_wait",    "Broadcast Init Wait (seconds)",          "int"),
        ("update_popup_kill_wait", "Update Popup Kill Wait (seconds)",       "int"),
    ]

    list_fields = [
        ("update_popup_processes",   "Update Popup Process Names (comma-separated)"),
        ("broadcast_stop_processes", "Broadcast Stop Processes (comma-separated)"),
        ("obs_stop_processes",       "OBS Stop Processes (comma-separated)"),
    ]

    bool_fields = [
        ("minimize_broadcast", "Minimize NVIDIA Broadcast after launch"),
        ("minimize_obs",       "Minimize OBS after launch"),
    ]

    vars_ = {}

    # Section header helper
    def section(text, row):
        lbl = tk.Label(win, text=text, anchor="w", font=("Segoe UI", 9, "bold"), fg="#888")
        lbl.grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(10, 2))

    row = 0
    section("— Executables & Paths —", row); row += 1
    for key, label, kind in simple_fields[:3]:
        tk.Label(win, text=label, anchor="w").grid(row=row, column=0, sticky="w", **pad)
        var = tk.StringVar(value=str(cfg.get(key, "")))
        vars_[key] = (var, kind)
        tk.Entry(win, textvariable=var, width=55).grid(row=row, column=1, **pad)
        if kind == "file":
            def browse_file(v=var):
                path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All", "*.*")])
                if path: v.set(path.replace("/", "\\"))
            tk.Button(win, text="...", command=browse_file).grid(row=row, column=2, padx=(0, 8))
        elif kind == "dir":
            def browse_dir(v=var):
                path = filedialog.askdirectory()
                if path: v.set(path.replace("/", "\\"))
            tk.Button(win, text="...", command=browse_dir).grid(row=row, column=2, padx=(0, 8))
        row += 1

    section("— Timing —", row); row += 1
    for key, label, kind in simple_fields[3:]:
        tk.Label(win, text=label, anchor="w").grid(row=row, column=0, sticky="w", **pad)
        var = tk.StringVar(value=str(cfg.get(key, "")))
        vars_[key] = (var, kind)
        tk.Entry(win, textvariable=var, width=20).grid(row=row, column=1, sticky="w", **pad)
        row += 1

    section("— Process Names —", row); row += 1
    for key, label in list_fields:
        tk.Label(win, text=label, anchor="w").grid(row=row, column=0, sticky="w", **pad)
        var = tk.StringVar(value=", ".join(cfg.get(key, [])))
        vars_[key] = (var, "list")
        tk.Entry(win, textvariable=var, width=55).grid(row=row, column=1, **pad)
        row += 1

    section("— Behaviour —", row); row += 1
    for key, label in bool_fields:
        var = tk.BooleanVar(value=cfg.get(key, False))
        vars_[key] = (var, "bool")
        tk.Checkbutton(win, text=label, variable=var, anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=2)
        row += 1

    def save():
        for key, (var, kind) in vars_.items():
            if kind == "list":
                cfg[key] = [x.strip() for x in var.get().split(",") if x.strip()]
            elif kind == "int":
                try:
                    cfg[key] = int(var.get().strip())
                except ValueError:
                    messagebox.showerror("Invalid", f"{key} must be a number.")
                    return
            elif kind == "bool":
                cfg[key] = var.get()
            else:
                cfg[key] = var.get().strip()
        save_config(cfg)
        if on_save:
            on_save(cfg)
        messagebox.showinfo("Saved", "Settings saved!")
        win.destroy()

    frame = tk.Frame(win)
    frame.grid(row=row, column=0, columnspan=3, pady=12)
    tk.Button(frame, text="Save",   command=save,        width=12).pack(side="left", padx=8)
    tk.Button(frame, text="Cancel", command=win.destroy, width=12).pack(side="left", padx=8)

    win.mainloop()

# ---------------------------------------------------------------------------
# Tray app
# ---------------------------------------------------------------------------
class BroadcastTray:
    def __init__(self, cfg):
        self.cfg    = cfg
        self.active = False
        self.icon   = None

    def update_icon(self):
        if self.icon:
            self.icon.icon  = make_icon(self.active)
            self.icon.title = (
                "Broadcast ON - right-click for options"
                if self.active else
                "Broadcast OFF - right-click for options"
            )

    def on_start(self, icon, item):
        if self.active:
            messagebox.showinfo("Already Running", "Broadcast and OBS are already running.")
            return
        self.active = True
        self.update_icon()
        threading.Thread(target=do_start, args=(self.cfg,), daemon=True).start()

    def on_stop(self, icon, item):
        if not self.active:
            messagebox.showinfo("Not Running", "Broadcast and OBS are not running.")
            return
        self.active = False
        self.update_icon()
        threading.Thread(target=do_stop, args=(self.cfg,), daemon=True).start()

    def on_settings(self, icon, item):
        def on_save(new_cfg):
            self.cfg = new_cfg
        threading.Thread(target=open_settings, args=(self.cfg, on_save), daemon=True).start()

    def on_exit(self, icon, item):
        icon.stop()
        os._exit(0)

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Start Broadcast + OBS", self.on_start),
            pystray.MenuItem("Stop Broadcast + OBS",  self.on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings",              self.on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit",                  self.on_exit),
        )
        self.icon = pystray.Icon(
            "BroadcastTray",
            make_icon(False),
            "Broadcast OFF - right-click for options",
            menu
        )
        self.icon.run()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cfg = load_config()
    if cfg is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Broadcast Tray - First Run",
            "Welcome! Let's configure your paths.\n\nClick OK to open settings."
        )
        root.destroy()
        cfg = dict(DEFAULT_CONFIG)
        open_settings(cfg)
        cfg = load_config()
        if cfg is None:
            sys.exit(0)

    app = BroadcastTray(cfg)
    app.run()
