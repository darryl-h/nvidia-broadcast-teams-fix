# Broadcast Tray

A Windows system tray app that starts and stops NVIDIA Broadcast + OBS together,
bridging NVIDIA Broadcast's effects into Microsoft Teams (and any other app using
the modern Windows camera stack).

## Why does this exist?

NVIDIA Broadcast 1.4.x registers as a DirectShow camera filter, not a proper
Windows camera driver. Modern apps like Microsoft Teams use the newer WinRT camera
API and cannot see DirectShow-only devices. OBS Virtual Camera acts as a bridge —
it takes the Broadcast feed and exposes it as a real Windows camera that Teams
can see.

---

## Prerequisites

### 1. NVIDIA Broadcast 1.4.x
Download from the NVIDIA website. During install, choose **Custom** and
**do not** let it update your GPU drivers if you are intentionally pinned to
a specific driver version.

> **Note:** If you previously had a newer version of Broadcast installed,
> uninstall it fully before installing 1.4.x. Leftover plugin DLLs from
> a newer version will cause the virtual camera pipeline to fail silently.

### 2. OBS Studio
Download from https://obsproject.com and install normally.
The Virtual Camera feature is built into OBS — no plugin needed.

### 3. Python 3.8+ (only needed to run from source)
Download from https://python.org. If you are using the compiled
`BroadcastTray.exe`, Python is not required.

---

## Installation

1. Place `BroadcastTray.exe` (or `broadcast_tray.py`) and `BroadcastTray.ico`
   in any folder you like, e.g. `C:\Tools\BroadcastTray\`

2. If running from source, install dependencies:
   ```
   pip install pystray pillow
   ```

3. Double-click `BroadcastTray.exe` to launch.
   On first run, a settings dialog will open — configure your paths and click Save.

4. The app will now sit in your system tray.

### Auto-start with Windows (optional)
Press `Win + R`, type `shell:startup`, press Enter.
Drop a shortcut to `BroadcastTray.exe` into that folder.

---

## Configuring OBS (one-time setup)

After launching OBS for the first time via the tray:

1. In OBS, click the **+** button under **Sources**
2. Choose **Video Capture Device**
3. Name it `Broadcast Camera` (or anything you like) → click OK
4. In the **Device** dropdown, select **Camera (NVIDIA Broadcast)**
5. Click OK — you should see the Broadcast feed with effects in the OBS preview
6. Click **Start Virtual Camera** in the Controls panel (bottom right)

OBS will remember this scene — you only need to do this once.

> **Tip:** The Start script automatically launches OBS. OBS will remember to
> start the Virtual Camera if you have previously enabled it.
> If Teams still doesn't see the OBS camera after starting, fully close
> and reopen Teams.

---

## Configuring Teams

1. Open Teams → Settings (... menu) → Devices
2. Under **Camera**, select **OBS Virtual Camera**
3. You should see your Broadcast feed with effects applied

---

## Using the tray app

Right-click the tray icon for the menu:

| Option | What it does |
|--------|-------------|
| **Start Broadcast + OBS** | Closes Teams, starts NVIDIA Broadcast, waits for it to initialize, kills the Broadcast update popup, then starts OBS. Icon turns green. Open Teams manually when ready. |
| **Stop Broadcast + OBS** | Gracefully stops OBS then NVIDIA Broadcast. Icon turns grey. Safe to game. |
| **Settings** | Opens the settings dialog to change paths or process names |
| **Exit** | Closes the tray app (does not stop Broadcast or OBS) |

---

## Settings reference

| Setting | Default | Description |
|---------|---------|-------------|
| NVIDIA Broadcast EXE | `...\NVIDIA Broadcast UI.exe` | Full path to the Broadcast executable |
| OBS EXE | `...\obs64.exe` | Full path to the OBS executable |
| OBS Working Directory | `...\obs-studio\bin\64bit` | Must match OBS EXE folder or OBS shows a locale error |
| Teams Process Name | `ms-teams` | Process name to kill when starting (check Task Manager if Teams doesn't close) |
| Broadcast Init Wait | `5` | Seconds to wait after Broadcast starts before launching OBS. Increase if OBS doesn't detect the virtual camera. |
| Broadcast Stop Processes | `Broadcast, NvVirtual, NvAFX` | Comma-separated process name fragments to kill on stop |
| OBS Stop Processes | `obs` | Comma-separated process name fragments to kill on stop |

---

## Compiling to EXE (from source)

```
pip install pyinstaller
pyinstaller --onefile --windowed --name BroadcastTray --icon BroadcastTray.ico broadcast_tray.py
```

The compiled exe will be in the `dist\` folder.

---

## Troubleshooting

**Teams still doesn't see OBS Virtual Camera**
Make sure OBS Virtual Camera is actually running (the button in OBS should say
"Stop Virtual Camera"). Then fully close and reopen Teams — Teams caches the
camera list at startup.

**OBS shows "Failed to find locale/en-US.ini"**
The OBS Working Directory setting is wrong. It must be the folder that contains
`obs64.exe`, not the root OBS folder.

**Broadcast update popup still appears**
Increase the Broadcast Init Wait time in Settings to give the update checker
more time to start before the tray app kills it.

**Virtual camera not showing in Broadcast**
This usually means leftover DLLs from a newer Broadcast version are in the
NvBroadcast.NvContainer plugins folder. Fully uninstall Broadcast, manually
delete `C:\Program Files\NVIDIA Corporation\NvBroadcast.NvContainer` and
`C:\Program Files\NVIDIA Corporation\NVIDIA Broadcast`, reboot, then reinstall.

**Stop doesn't kill everything**
Open Task Manager and check the exact process names. Add them to the appropriate
stop process list in Settings.
