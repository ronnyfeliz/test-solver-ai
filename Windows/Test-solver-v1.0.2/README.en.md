[🇪🇸 Español](README.md) · 🇺🇸 **English**

# 🎯 Test Solver AI v1.0.2 — Windows

Test Solver AI for **Windows 10/11**.

> General project documentation (features, supported AI providers,
> security and credits): [main README](../../README.md)

---

## 🚀 Quick start (executable)

1. Download `test_solver_v1.0.2.exe` from the [official v1.0.2 — Windows Release](https://github.com/ronnyfeliz/test-solver-ai/releases/tag/windows-v1.0.2).
2. Run it as administrator: if the current provider's API key is missing, **Settings** opens automatically.
3. Paste your API key (stored **locally only**, next to the exe).
4. Press **Start service** and use **F8** on any question of your online exam.

> Closing the window only minimizes it to the background; use **Exit** or **F9** to actually quit.
> Check the Task Manager to verify the service is running before using the hotkey.

## 🛠️ Run from source

```bash
cd code_source_v1.0.2
pip install requests pillow keyboard pyinstaller
python test_solver_v1.0.2.py
```

Requirements: Windows 10/11, Python 3.10+, ≥ 1280x720 display recommended.

## 📦 Build the executable

```bash
cd code_source_v1.0.2
python -m PyInstaller test_solver_v1.0.2.spec --noconfirm --clean
# output in dist/test_solver_v1.0.2.exe
```

## ⚙️ Configuration

- The `config.json` file is created **next to the executable/script** (never in system-relative paths). Clean template: [`config.example.json`](code_source_v1.0.2/config.example.json).
- From **Settings** you can change provider, key, endpoint, model, language and hotkeys; everything applies live while the service is running.

## 🗂️ Structure

```
├── code_source_v1.0.2/     # Source code + PyInstaller spec
│   ├── media/fonts/        # Open Sans (SIL OFL)
│   ├── config.example.json # Clean configuration template
│   └── test_solver_v1.0.2.py
├── media/                  # Project icons
└── README.md               # Windows version documentation
```

---

⚠️ Educational tool: use it at your own discretion and respect your institution's rules.
