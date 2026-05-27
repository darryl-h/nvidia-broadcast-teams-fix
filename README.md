# Broadcast Tray

A Windows system tray utility that manages NVIDIA Broadcast and OBS together,
bridging NVIDIA Broadcast's AI camera effects into Microsoft Teams and other
modern video calling apps.

---

## Why does this exist? (The short version)

NVIDIA's recent GPU drivers for the RTX 4000 series have introduced stability
and performance regressions. Driver version **566.36** is widely regarded by the
community as the most stable option for RTX 4XXX cards, and is the version the
author of this tool uses personally. You can download it here:

> https://www.nvidia.com/en-us/drivers/details/237752/

The catch: NVIDIA Broadcast 2.x requires a newer driver and will refuse to run
properly on 566.36. The latest version of Broadcast that works correctly with
566.36 is **1.4.0.39**, available here:

> https://international.download.nvidia.com/Windows/broadcast/1.4.0.39/NVIDIA_Broadcast_v1.4.0.39.exe

---

## Why doesn't Broadcast just work with Teams? (The longer version)

NVIDIA Broadcast 1.4.x registers its virtual camera as a **DirectShow** filter.
DirectShow is an older Windows camera API that has been around since the late
1990s and is still widely supported.

Modern applications like Microsoft Teams, Zoom, and Slack have moved to the
newer **WinRT** camera API introduced with Windows 10. WinRT only recognises
cameras that are registered as proper Windows camera devices and it completely
ignores DirectShow-only filters like the one Broadcast 1.4.x installs.

The result: Teams cannot see NVIDIA Broadcast as a camera source at all.

**OBS Studio** solves this. OBS still uses DirectShow internally (so it can see
Broadcast), and its **Virtual Camera** feature re-exposes the feed as a proper
WinRT-compatible Windows camera device. Every modern app can then see it.

So the chain looks like this:

```
Physical Camera (IE: Logitech BRIO)
        ↓
NVIDIA Broadcast 1.4.x  (AI effects: background blur, replacement, etc.)
        ↓  [DirectShow]
OBS Studio  (receives Broadcast feed, re-exposes via Virtual Camera)
        ↓  [WinRT / Windows Camera Driver]
Microsoft Teams / Zoom / Slack / any modern app
```

Yes, it is annoying. Yes, it is entirely caused by NVIDIA shipping driver
updates that broke a previously working product. This tool exists to make the
workaround as painless as possible.

### Apps affected (require the OBS bridge)
- Microsoft Teams (new)
- Zoom (newer versions)
- Slack (desktop app)
- Google Meet / Webex (browser-based, uses browser WinRT integration)
- Windows Camera app

### Apps that work with Broadcast directly (no bridge needed)
- Discord
- OBS itself
- Streamlabs
- Any app still using the legacy DirectShow camera API

---

## Prerequisites

### 1. NVIDIA GPU Driver 566.36
Download from: https://www.nvidia.com/en-us/drivers/details/237752/

During install choose **Custom** and uncheck GeForce Experience if you do not
want it. Do **not** let any other software automatically update your driver.

### 2. NVIDIA Broadcast 1.4.0.39
Download from:
https://international.download.nvidia.com/Windows/broadcast/1.4.0.39/NVIDIA_Broadcast_v1.4.0.39.exe

During install choose **Custom** and do **not** allow it to update your GPU driver.

> **Important:** If you previously had a newer version of Broadcast installed,
> uninstall it fully before installing 1.4.0.39. Leftover plugin DLLs from a
> newer version will cause the virtual camera pipeline to silently fail. After
> uninstalling, manually delete these folders if they still exist:
> - `C:\Program Files\NVIDIA Corporation\NvBroadcast.NvContainer`
> - `C:\Program Files\NVIDIA Corporation\NVIDIA Broadcast`
>
> Then reboot before reinstalling.

### 3. OBS Studio
Download from: https://obsproject.com

Install normally. The Virtual Camera feature is built in — no plugin needed.

---

## Installation

1. Place `BroadcastTray.exe` in any permanent folder, e.g.
   `C:\Tools\BroadcastTray\`

2. Double-click `BroadcastTray.exe`. On first run a settings dialog will open.
   Configure your paths and click **Save**.

3. The app will now sit quietly in your system tray.

### Auto-start with Windows (optional)
Press `Win + R`, type `shell:startup`, press Enter.
Drop a shortcut to `BroadcastTray.exe` into that folder.

---

## Configuring OBS (one-time setup)

Do this after launching OBS for the first time via the tray:

1. In OBS, click **+** under **Sources**
2. Choose **Video Capture Device**
3. Name it `Nvidia Broadcast Camera`
4. Click **OK**
5. In the **Device** dropdown select **Camera (NVIDIA Broadcast)**
6. Click OK (You should see your Broadcast feed with effects in the OBS preview)
7. Click **Start Virtual Camera** in the Controls panel (bottom right)

OBS remembers this configuration. You only need to do this once.

---

## Configuring Teams

1. Open Teams → **Settings** → **Devices**
2. Under **Camera**, select **OBS Virtual Camera**
3. You should see your Broadcast feed with effects applied

> **Note:** Teams must be started *after* OBS Virtual Camera is running or it
> will not see it. The tray app handles this automatically, and it closes Teams
> before starting Broadcast and OBS, then reminds you to reopen Teams when
> everything is ready.

---

## Using the tray app

Right-click the tray icon for the menu:

| Option | What it does |
|--------|-------------|
| **Start Broadcast + OBS** | Checks if Teams is running and offers to close it, starts NVIDIA Broadcast, waits for it to initialise, kills the update popup, starts OBS, then reminds you to open Teams. Icon turns green. |
| **Stop Broadcast + OBS** | Gracefully stops OBS then NVIDIA Broadcast. Icon turns grey. Safe to game. |
| **Settings** | Opens the settings dialog |
| **Exit** | Closes the tray app completely |

---

## Settings reference

### Executables & Paths

| Setting | Default | Description |
|---------|---------|-------------|
| NVIDIA Broadcast EXE | `...\NVIDIA Broadcast UI.exe` | Full path to the Broadcast executable |
| OBS EXE | `...\obs64.exe` | Full path to the OBS executable |
| OBS Working Directory | `...\obs-studio\bin\64bit` | Must match the folder containing obs64.exe — if set incorrectly OBS will show a locale error on launch |

### Timing

These two settings exist because NVIDIA Broadcast has no option to disable its
update checker, and it launches the popup asynchronously after startup — meaning
we have to wait for it to appear before we can kill it. If you see the popup
slipping through, increase the wait time.

| Setting | Default | Description |
|---------|---------|-------------|
| Broadcast Init Wait | `5` | How long to wait (seconds) after Broadcast starts before launching OBS. OBS needs to find the Broadcast virtual camera at startup — if OBS launches too fast, it won't see it. Increase this if OBS shows a blank camera source. |
| Nvidia Broadcast Update Popup Wait | `8` | How long to wait (seconds) after Broadcast starts before killing the update nag popup. The popup appears a few seconds after Broadcast launches, so this needs to be long enough to let it appear before we kill it. If the popup is still slipping through, increase this value. |

### Process Names

These settings tell the app which processes to look for when detecting, closing,
or stopping each application. The values are fragments — "Broadcast" will match
any process whose name contains the word "Broadcast". If an app isn't being
detected or stopped correctly, open Task Manager, find the exact process name,
and add it (or a unique fragment of it) to the relevant field.

| Setting | Default | Description |
|---------|---------|-------------|
| Teams Process Name | `ms-teams` | Fragment used to detect whether Teams is running and to close it before starting Broadcast. If Teams isn't being closed, check its exact process name in Task Manager. |
| Update Popup Process Names | `NvBroadcastInstaller, OTAUtility, NvBroadcastInstallerOTA` | Comma-separated list of process name fragments to kill when suppressing the NVIDIA Broadcast update popup. If the popup still appears, open Task Manager while it is visible, find the process name, and add it here. |
| Broadcast Stop Processes | `Broadcast, NvVirtual, NvAFX` | Comma-separated fragments used to find and kill all Broadcast-related processes when stopping. |
| OBS Stop Processes | `obs` | Comma-separated fragments used to find and kill OBS when stopping. |

### Behaviour

| Setting | Default | Description |
|---------|---------|-------------|
| Minimize NVIDIA Broadcast after launch | Off | Automatically minimizes Broadcast to taskbar after it starts |
| Minimize OBS after launch | Off | Automatically minimizes OBS to taskbar after it starts (waits 3 seconds for OBS to fully open first) |

---

## Troubleshooting

**Teams still doesn't see OBS Virtual Camera**
Make sure OBS Virtual Camera is running (the button in OBS should say
"Stop Virtual Camera"). Then fully close and reopen Teams — Teams caches the
camera list at startup and won't detect new devices mid-session.

**OBS shows "Failed to find locale/en-US.ini"**
The OBS Working Directory setting is wrong. It must be the same folder that
contains obs64.exe.

**The NVIDIA Broadcast update popup still appears**
Open Task Manager while the popup is visible, note the exact process name,
then add it to the Update Popup Process Names list in Settings. Also try
increasing the Update Popup Kill Wait time.

**Virtual camera not showing inside NVIDIA Broadcast**
This usually means leftover DLLs from a newer Broadcast version are interfering.
Fully uninstall Broadcast, manually delete the two folders listed in the
Prerequisites section, reboot, then reinstall 1.4.0.39.

**BroadcastTray.exe is still in Task Manager after clicking Exit**
This was a known bug fixed in the current version. Recompile or redownload.

**Stop doesn't kill all processes**
Open Task Manager and check the exact process names still running. Add them
to the appropriate stop process list in Settings.

---

## Building from source

```
pip install pystray pillow pyinstaller
pyinstaller --onefile --windowed --name BroadcastTray --icon BroadcastTray.ico --add-data "BroadcastTray.ico;." broadcast_tray.py
```

The compiled exe will be in the `dist\` folder. The only file you need to
distribute is `BroadcastTray.exe` — the config file is created automatically
on first run next to the exe.
