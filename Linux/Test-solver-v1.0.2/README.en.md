[🇪🇸 Español](README.md) · 🇺🇸 **English**

# 🎯 Test Solver AI v1.0.2 — Linux

Test Solver AI for **Linux** (X11 and Wayland).

---

## 🚀 Quick start (executable)

1. Download `test_solver_v1.0.2` from the official v1.0.2 — Linux Release.
2. Make it executable and run it with **sudo** (required for global keyboard
   hotkeys):

   ```bash
   chmod +x test_solver_v1.0.2
   sudo ./test_solver_v1.0.2
   ```

   > 💡 **Alternative without `sudo` or passwords**: add your user to the
   > `input` group, log out and log back in:
   >
   > ```bash
   > sudo usermod -aG input $USER
   > ```
   >
   > Then you can launch the app directly as your regular user — even with a
   > double-click from a desktop `.desktop` launcher.

3. If the current provider's API key is missing, **Settings** opens
   automatically.
4. Paste your API key (stored **locally only**, next to the binary).
5. Press **Start service** and use **F8** on any question of your online exam.

> Closing the window only minimizes it to the background; use **Exit** or
> **F9** to actually quit.

## 🔑 Permissions and graphical session on Linux

- **Global hotkeys**: the `keyboard` library reads `/dev/input` directly, so
  privileges are required: run with `sudo`, or add your user to the `input`
  group (`sudo usermod -aG input $USER`, log out and back in) to launch it as
  a regular user. Without privileges the *Start service* button shows an
  explanatory error.
- **Screen capture**:
  - On **X11** it works out of the box (Pillow/XCB, or `scrot`/`maim` if
    installed).
  - On **Wayland** native tools are used when available: `grim`
    (Sway/wlroots), `gnome-screenshot` (GNOME) or `spectacle` (KDE). Install
    the one for your desktop if capture fails, e.g.:
    `sudo apt install grim` / `sudo pacman -S grim`.

## 🛠️ Run from source

```bash
cd code_source_v1.0.2
pip install -r requirements.txt
sudo python3 test_solver_v1.0.2.py
```

Requirements: Python 3.10+, Tkinter (`python3-tk` on Debian/Ubuntu), ≥
1280x720 display recommended.

## 📦 Build the executable

```bash
cd code_source_v1.0.2
./build_linux.sh
# output in dist/test_solver_v1.0.2
```

or manually:

```bash
python3 -m PyInstaller test_solver_v1.0.2.spec --noconfirm --clean
```

## ⚙️ Configuration

- The `config.json` file is created **next to the binary/script** (never in
  system-relative paths). Clean template:
  [`config.example.json`](code_source_v1.0.2/config.example.json).
- From **Settings** you can change provider, key, endpoint, model, language
  and hotkeys; everything applies live while the service is running.
- The bundled Open Sans font is installed per-user
  (`~/.local/share/fonts/TestSolverAI`) on first launch; if unavailable the
  closest system font is used.

## 🗂️ Structure

```
├── code_source_v1.0.2/     # Source code + PyInstaller spec (Linux)
│   ├── media/fonts/        # Open Sans (SIL OFL)
│   ├── requirements.txt    # Python dependencies
│   ├── build_linux.sh      # Binary build script
│   ├── config.example.json # Clean configuration template
│   ├── test_solver_v1.0.2.spec
│   └── test_solver_v1.0.2.py
├── media/                  # Project icons
├── README.md               # Documentación (Español)
└── README.en.md            # Documentation (English)
```

---

⚠️ Educational tool: use it at your own discretion and respect your institution's rules.
