[🇪🇸 Español](README.md) · 🇺🇸 **English**

<p align="center">
  <img src="Windows/Test-solver-v1.0.2/media/test-solver-v1.0.2.png" alt="Test Solver AI logo" width="140">
</p>

# 🎯 Test Solver AI

Cross-platform **desktop tool** that analyzes multiple-choice questions on your
screen using vision AI and instantly shows the answer in a floating overlay.

> **F8** → capture and analyze the screen · **F9** → close the application
>
> 🌐 **Official website:** [test-solver-ai.netlify.app](https://test-solver-ai.netlify.app/)

---

## ✨ Features

- **One-hotkey analysis**: optimized screen capture → vision LLM → explained answer.
- **Always-on-top floating overlay** with loading / result / error views, copy answer and retry.
- **Main panel** with real service status, uptime, last check and provider/model info.
- **Real state machine**: `stopped / starting / running / stopping / down` states polled from the real system hook, with a watchdog that detects crashes and lets you recover the service.
- **Extensible multi-provider support** with real free tiers.
- **Full ES/EN bilingual UI**, applied live without restarting.
- Embedded **Open Sans** typography (no installation required) and modern rounded buttons.
- Toast notifications, single instance, local persistent configuration.

## 🔌 Supported providers

| Provider | Cost | Vision (screenshots) | Note |
|---|---|---|---|
| **Groq** (`qwen/qwen3.6-27b`) | Free* | ✅ | Per-minute/per-day quota depending on the model |
| **Google Gemini (AI Studio)** | Free* | ✅ | Free tier, no card required; Flash ≈10 rpm/250 day |
| **OpenRouter** (`:free` models) | Free* | ✅ model-dependent | Gemma 4, Nemotron Nano VL, etc.; ~50 req/day |
| **OpenCode Zen (Big Pickle)** | Free (temporary) | ❌ text/code only | Requires an OpenCode Zen key |
| **Official DeepSeek** | Paid (affordable) | ❌ | `deepseek-chat` / `deepseek-reasoner` |
| **OpenAI** | Paid | ✅ gpt-4o-mini | Requires prepaid credit |
| **Custom** | Varies | Varies | Any OpenAI-compatible endpoint |

\* Subject to each service's current quotas.

The app detects retired models (e.g. Groq's old `meta-llama/*`, now HTTP 404)
and **automatically repairs** the configuration on startup.

## 📦 Platforms

| Platform | Status | Documentation | Download |
|---|---|---|---|
| **Windows** | ✅ v1.0.2 | [`Windows/Test-solver-v1.0.2/README.en.md`](Windows/Test-solver-v1.0.2/README.en.md) | [⬇️ Release v1.0.2](https://github.com/ronnyfeliz/test-solver-ai/releases/tag/windows-v1.0.2) |
| **Linux** | ✅ v1.0.2 (X11/Wayland) | [`Linux/Test-solver-v1.0.2/README.en.md`](Linux/Test-solver-v1.0.2/README.en.md) | [⬇️ Linux Release v1.0.2](https://github.com/ronnyfeliz/test-solver-ai/releases/tag/linux-v1.0.2) |

Each platform folder contains its source code, installation/run instructions
and the specific packaging process.

> 🐧 **Quick notes for Linux**: global hotkeys require running the app with
> `sudo` (the `keyboard` library reads `/dev/input` directly). On X11 screen
> capture works out of the box; on Wayland native tools are used (`grim`,
> `gnome-screenshot` or `spectacle`). See the platform README for details.

## 🔒 Security & privacy

- No credentials are hardcoded in the source code.
- API keys are stored **locally only** (never sent to logs: every error is sanitized before being displayed).
- This repository excludes via `.gitignore`: `config.json`, logs, build artifacts, internal backups and personal notes.
- If you ever leaked a key (e.g. in an old backup), **revoke it** in your provider's dashboard before publishing.

## 👥 Credits

| Role | Person |
|---|---|
| **Original author and creator of the application** | **Alex Hatton** |
| **GUI collaborator** (modern graphical interface, architecture and packaging) | **Ronny Feliz** · [github.com/ronnyfeliz](https://github.com/ronnyfeliz) |

### Technologies used
Python · Tkinter · Pillow · keyboard · Requests · PyInstaller · REST APIs (Groq, Gemini, OpenRouter) · OpenCode · Antigravity IDE

- **Created:** March 19, 2026
- **Last updated:** August 24, 2026

## 💼 Collaborator / Developer — Ronny Feliz

Responsible for developing the modern graphical interface, the architecture
and the packaging of Test Solver AI.

| Contact | Link |
|---|---|
| 🌐 Portfolio | [ronnyfeliz.github.io](https://ronnyfeliz.github.io/) |
| 🐙 GitHub | [@ronnyfeliz](https://github.com/ronnyfeliz) |
| 💼 LinkedIn | [in/ronnyfeliz2](https://www.linkedin.com/in/ronnyfeliz2/) |
| ✉️ Email | [blxst608@gmail.com](mailto:blxst608@gmail.com) |

---

⚠️ Educational tool: use it at your own discretion and respect your institution's rules.
