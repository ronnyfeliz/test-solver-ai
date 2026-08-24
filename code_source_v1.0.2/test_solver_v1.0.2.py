# -*- coding: utf-8 -*-
"""
Test Solver AI - v1.0.2
-----------------------
Screen-analysis assistant with a real, observable service lifecycle.

Created:            March 19, 2026
Last updated:       August 23, 2026
Collaborator:       Ronny Feliz (https://github.com/ronnyfeliz)

Key design points:
  * Open Sans is the global UI typeface (bundled + privately registered at
    runtime). Consolas is used ONLY for technical tokens (hotkeys / version)
    to improve differentiation.
  * ServiceController is the single source of truth for the service state.
    It never trusts an internal flag: it probes the REAL state of the global
    keyboard hooks and their OS listener thread every second (watchdog), so
    external/unexpected terminations are detected automatically.
  * Launching the exe only opens the control window; it NEVER auto-starts
    the service. The service must be started explicitly by the user.
"""

import os
import sys

# Redirect stdout and stderr to solver_error.log to capture any windowed crashes
try:
    log_file = open("solver_error.log", "a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
except Exception:
    pass

import io
import json
import time
import queue
import base64
import socket
import ctypes
import threading
import re
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import keyboard
import requests
from PIL import ImageGrab, Image

# Configuration settings
SINGLE_INSTANCE_PORT = 49281
TEST_SOLVER_VERSION = "v1.0.2"


def _app_dir():
    """Directory that hosts the running app (exe dir when frozen)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    override = os.environ.get("TS_CONFIG_DIR")
    if override:
        return override
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    return os.path.join(_app_dir(), "config.json")


CONFIG_FILE = _config_path()

# Groq retired all Llama vision models; these IDs now return HTTP 404.
DEPRECATED_GROQ_MODELS = (
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
)

DEFAULT_CONFIG = {
    "current_provider": "groq",
    "language": "es",
    "hotkey_analyze": "f8",
    "hotkey_close": "f9",
    "screenshot_quality": 85,
    "max_width": 1600,
    "providers": {
        "groq": {
            "api_key": "",
            "model": "qwen/qwen3.6-27b",
            "base_url": "https://api.groq.com/openai/v1"
        },
        "openai": {
            "api_key": "",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1"
        },
        "gemini": {
            "api_key": "",
            "model": "gemini-2.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta"
        },
        "openrouter": {
            "api_key": "",
            "model": "google/gemma-4-31b-it:free",
            "base_url": "https://openrouter.ai/api/v1"
        },
        "deepseek": {
            "api_key": "",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1"
        },
        "opencode": {
            "api_key": "",
            "model": "big-pickle",
            "base_url": "https://opencode.ai/zen/v1"
        },
        "custom": {
            "api_key": "",
            "model": "",
            "base_url": ""
        }
    }
}

# Global variables
config = {}
_is_analyzing = False
_overlay = None
_settings_window = None
_main_window = None
_controller = None          # ServiceController (single source of truth)
_queue = queue.Queue()
_instance_socket = None
_ui_listeners = []          # UI subscribers for service-state snapshots

# ============================================================================
# VISUAL IDENTITY - Catppuccin Mocha palette
# ============================================================================
COLORS = {
    "bg": "#1e1e2e",            # Mocha Base      - main background
    "panel": "#181825",         # Mocha Mantle    - cards / inputs
    "header": "#11111b",        # Mocha Crust     - header bars
    "text": "#cdd6f4",          # Mocha Text
    "subtext": "#a6adc8",       # Mocha Subtext0
    "muted": "#7f849c",         # Mocha Overlay0  - disabled fg / idle dot
    "surface": "#313244",       # Mocha Surface0  - buttons
    "surface_hi": "#414559",    # Mocha Surface1  - button hover
    "border": "#45475a",        # Mocha Surface1  - card borders
    "accent": "#b4befe",        # Lavender        - primary accent
    "green": "#a6e3a1",         # Mocha Green     - success / start
    "red": "#f38ba8",           # Mocha Red       - danger / stop / errors
    "yellow": "#f9e2af",        # Mocha Yellow    - starting / warnings
    "orange": "#fab387",        # Mocha Peach     - stopping
    "teal": "#94e2d5"           # Mocha Teal      - info details
}

# Button palettes: normal / hover / press (+ shared disabled & error flash).
# Red buttons use an intense, high-contrast red (#e5484d family) so white
# text stays perfectly legible while clearly signaling the destructive/
# stopping action (contrast ratio vs. white ≈ 4.9:1).
BTN_PALETTES = {
    "green":   {"bg": "#3fb950",   "fg": "#ffffff", "hover": "#4cc25d",
                "press": "#34a044", "hover_fg": "#ffffff"},
    "red":     {"bg": "#e5484d",   "fg": "#ffffff", "hover": "#f05e63",
                "press": "#c73a3f", "hover_fg": "#ffffff"},
    "surface": {"bg": COLORS["surface"], "fg": COLORS["text"],
                "hover": COLORS["surface_hi"], "press": "#51576d"},
    "accent":  {"bg": COLORS["accent"],  "fg": COLORS["header"],
                "hover": "#c7d3fe", "press": "#9db1f7"},
    "ghost_danger": {"bg": COLORS["header"], "fg": "#ff8a92",
                     "hover": "#e5484d", "press": "#c73a3f",
                     "hover_fg": "#ffffff"}
}
BTN_DISABLED_BG = "#3a3f54"
BTN_DISABLED_FG = COLORS["muted"]
BTN_ERROR_FLASH_MS = 900

# ============================================================================
# TYPOGRAPHY - Open Sans as the global application font
# ----------------------------------------------------------------------------
# Open Sans is bundled with the app and registered privately at runtime
# (AddFontResourceExW + FR_PRIVATE), so it works even when the font is not
# installed system-wide. Justified exception: 'Consolas' (monospace) is used
# exclusively for technical tokens (hotkeys, version badge): fixed-width
# aligned glyphs make key names such as "F8"/"F9" easier to scan.
# ============================================================================
FONT_FAMILY = "Open Sans"
MONO_FAMILY = "Consolas"
FONT_DIR_NAME = os.path.join("media", "fonts")
_OPEN_SANS_FILES = [
    "OpenSans-Regular.ttf", "OpenSans-Italic.ttf", "OpenSans-SemiBold.ttf",
    "OpenSans-Bold.ttf", "OpenSans-ExtraBold.ttf"
]
_fonts_registered = False


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.abspath(os.path.join(base_path, relative_path))
    if os.path.exists(path):
        return path
    fallback_path = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), relative_path))
    return fallback_path


def register_open_sans_fonts():
    """Privately register the bundled Open Sans TTFs for this process."""
    global _fonts_registered
    if _fonts_registered:
        return True
    FR_PRIVATE = 0x10
    gdi32 = ctypes.windll.gdi32
    loaded_any = False
    for fname in _OPEN_SANS_FILES:
        fpath = get_resource_path(os.path.join(FONT_DIR_NAME, fname))
        if os.path.exists(fpath):
            try:
                res = gdi32.AddFontResourceExW(ctypes.c_wchar_p(fpath), FR_PRIVATE, 0)
                if res:
                    loaded_any = True
            except Exception:
                pass
    _fonts_registered = loaded_any
    return loaded_any


def font(size, weight="normal", slant="roman", underline=False,
         mono=False, overstrike=False):
    """Build a Tk font tuple in the global family (Open Sans)."""
    family = MONO_FAMILY if mono else FONT_FAMILY
    styles = []
    if weight == "bold":
        styles.append("bold")
    if slant == "italic":
        styles.append("italic")
    if underline:
        styles.append("underline")
    if overstrike:
        styles.append("overstrike")
    return (family, size) + tuple(styles)


def enable_dpi_awareness():
    """DPI awareness so fonts/layout are crisp and never clipped by scaling."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# Localization Dictionary
TRANSLATIONS = {
    "es": {
        "app_title": "Test Solver AI",
        "main_subtitle": "Panel de control del servicio",
        "settings_title": "Configuración - Test Solver AI",
        "api_config_title": "PROVEEDOR DE IA",
        "section_prefs": "PREFERENCIAS",
        "section_service": "SERVICIO",
        "lbl_provider": "Proveedor",
        "lbl_api_key": "Clave API",
        "lbl_base_url": "URL Base (Opcional)",
        "lbl_model": "Modelo de IA",
        "lbl_language": "Idioma de Respuestas",
        "lbl_hotkey_analyze": "Hotkey Capturar",
        "lbl_hotkey_close": "Hotkey Cerrar",
        "lbl_show_key": "Ver",
        "prov_depends": "Depende del endpoint",
        "prov_label_groq": "Groq",
        "prov_label_gemini": "Google Gemini (AI Studio)",
        "prov_label_openrouter": "OpenRouter",
        "prov_label_opencode": "OpenCode Zen (Big Pickle)",
        "prov_label_deepseek": "DeepSeek (oficial)",
        "prov_label_openai": "OpenAI",
        "prov_label_custom": "Personalizado",
        "lbl_service_status": "Estado del Servicio",
        "status_running": "En ejecución",
        "status_stopped": "Detenido",
        "status_starting": "Iniciando…",
        "status_stopping": "Deteniendo…",
        "status_crashed": "Terminó inesperadamente",
        "btn_start_service": "Iniciar servicio",
        "btn_stop_service": "Detener servicio",
        "btn_test": "Probar conexión",
        "btn_save": "Guardar",
        "btn_cancel": "Cancelar",
        "btn_credits": "Créditos",
        "btn_settings": "Configuración",
        "btn_exit": "Salir",
        "btn_copy": "Copiar",
        "btn_copied": "Copiado ✓",
        "prov_free": "Gratis",
        "prov_paid": "Pago",
        "prov_freemium": "Nivel gratuito",
        "prov_key_required": "Requiere clave API",
        "prov_no_key": "Sin clave API",
        "prov_vision": "Visión",
        "prov_text_only": "Solo texto",
        "prov_limits": "Límites",
        "prov_note_openrouter": "Modelos «:free» limitados; otros modelos son de pago.",
        "prov_note_groq": "Cuota gratuita por minuto/día según modelo.",
        "prov_note_gemini": "Nivel gratuito de AI Studio sin tarjeta; Flash ≈10 rpm/250 día.",
        "prov_note_deepseek": "API oficial de pago (económica); sin visión.",
        "prov_note_opencode": "Big Pickle gratis por tiempo limitado; solo texto/código.",
        "prov_note_openai": "Requiere crédito prepagado; gpt-4o-mini tiene visión.",
        "prov_note_custom": "Define tu propio endpoint compatible con OpenAI.",
        "credits_title": "Créditos",
        "credits_author_label": "Autor original",
        "credits_author_name": "Alex Hatton",
        "credits_author_desc": "Autor y creador de la aplicación original.",
        "credits_collab_label": "Colaborador",
        "credits_collab_name": "Ronny Feliz",
        "credits_collab_desc": "Responsable de la GUI (interfaz gráfica): "
                               "diseño moderno, arquitectura y empaquetado.",
        "credits_github": "GitHub:",
        "credits_tech_title": "Tecnologías utilizadas",
        "credits_tech_list": ("Python · Tkinter · Pillow · keyboard · Requests · "
                              "PyInstaller · APIs REST (Groq, Gemini, OpenRouter) · "
                              "OpenCode · Antigravity IDE"),
        "credits_created_label": "Creación:",
        "credits_created_value": "19 de marzo de 2026",
        "credits_updated_label": "Última actualización:",
        "credits_updated_value": "23 de agosto de 2026",
        "credits_close": "Cerrar",
        "toast_title": "🚀 Test Solver AI",
        "toast_msg": "Servicio en ejecución. {hotkey} para analizar.",
        "toast_msg_stopped": "Servicio detenido. Inícialo desde el panel principal.",
        "toast_background": "La app sigue activa en segundo plano. Ejecuta el .exe de nuevo para reabrir el panel.",
        "err_connection": "Error de conexión. Revisa tu internet.",
        "err_timeout": "Tiempo de espera agotado.",
        "err_invalid_key": "Clave API inválida o vacía.",
        "success_conn": "✓ Conexión exitosa",
        "analyzing": "Analizando pantalla…",
        "calling_api": "Llamando a la API…",
        "overlay_title": "🤖 Test Solver AI",
        "error_title": "⚠️ ERROR DE EJECUCIÓN",
        "suggestion": "💡 Sugerencia:\n",
        "suggestion_msg": "Revisa la clave de API y la conexión del proveedor en Ajustes.",
        "btn_retry": "🔄 Reintentar",
        "msg_saved": "Ajustes guardados correctamente.",
        "msg_hotkey_err": "Error al registrar hotkeys.",
        "msg_hotkey_invalid": "Hotkeys inválidas: deben ser distintas y usar un formato válido (ej. f8).",
        "msg_service_started": "Servicio iniciado correctamente.",
        "msg_service_stopped": "Servicio detenido correctamente.",
        "msg_service_err": "Error al cambiar el estado del servicio.",
        "msg_service_crashed": "El servicio terminó inesperadamente.",
        "msg_stop_failed": "No se pudo liberar los hooks del teclado.",
        "msg_exit_confirm": "¿Seguro que quieres salir de Test Solver AI?",
        "msg_exit_title": "Salir",
        "banner_no_key_title": "⚠ Falta configurar tu clave API",
        "banner_no_key_msg": "Configura un proveedor para habilitar el análisis de pantalla.",
        "banner_btn": "Configurar ahora",
        "info_provider": "PROVEEDOR",
        "info_model": "MODELO",
        "info_language": "IDIOMA",
        "info_hotkey_analyze": "CAPTURAR",
        "info_hotkey_close": "CERRAR APP",
        "uptime_label": "Tiempo activo:",
        "last_check_label": "Última comprobación:",
        "monitor_hint": "Vigilancia automática cada segundo",
        "lang_es": "Español",
        "lang_en": "English"
    },
    "en": {
        "app_title": "Test Solver AI",
        "main_subtitle": "Service control panel",
        "settings_title": "Configuration - Test Solver AI",
        "api_config_title": "AI PROVIDER",
        "section_prefs": "PREFERENCES",
        "section_service": "SERVICE",
        "lbl_provider": "Provider",
        "lbl_api_key": "API Key",
        "lbl_base_url": "Base URL (Optional)",
        "lbl_model": "AI Model",
        "lbl_language": "Response Language",
        "lbl_hotkey_analyze": "Capture Hotkey",
        "lbl_hotkey_close": "Close Hotkey",
        "lbl_show_key": "Show",
        "prov_depends": "Depends on endpoint",
        "prov_label_groq": "Groq",
        "prov_label_gemini": "Google Gemini (AI Studio)",
        "prov_label_openrouter": "OpenRouter",
        "prov_label_opencode": "OpenCode Zen (Big Pickle)",
        "prov_label_deepseek": "DeepSeek (official)",
        "prov_label_openai": "OpenAI",
        "prov_label_custom": "Custom",
        "lbl_service_status": "Service Status",
        "status_running": "Running",
        "status_stopped": "Stopped",
        "status_starting": "Starting…",
        "status_stopping": "Stopping…",
        "status_crashed": "Terminated unexpectedly",
        "btn_start_service": "Start service",
        "btn_stop_service": "Stop service",
        "btn_test": "Test connection",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "btn_credits": "Credits",
        "btn_settings": "Settings",
        "btn_exit": "Exit",
        "btn_copy": "Copy",
        "btn_copied": "Copied ✓",
        "prov_free": "Free",
        "prov_paid": "Paid",
        "prov_freemium": "Free tier",
        "prov_key_required": "Requires API key",
        "prov_no_key": "No API key",
        "prov_vision": "Vision",
        "prov_text_only": "Text only",
        "prov_limits": "Limits",
        "prov_note_openrouter": "«:free» models are limited; other models are paid.",
        "prov_note_groq": "Free quota per minute/day depending on model.",
        "prov_note_gemini": "AI Studio free tier, no card; Flash ≈10 rpm/250 day.",
        "prov_note_deepseek": "Official paid API (cheap); no vision.",
        "prov_note_opencode": "Big Pickle free for a limited time; text/code only.",
        "prov_note_openai": "Requires prepaid credit; gpt-4o-mini has vision.",
        "prov_note_custom": "Define your own OpenAI-compatible endpoint.",
        "credits_title": "Credits",
        "credits_author_label": "Original author",
        "credits_author_name": "Alex Hatton",
        "credits_author_desc": "Author and creator of the original application.",
        "credits_collab_label": "Collaborator",
        "credits_collab_name": "Ronny Feliz",
        "credits_collab_desc": "Responsible for the GUI (graphical "
                               "interface): modern design, architecture "
                               "and packaging.",
        "credits_github": "GitHub:",
        "credits_tech_title": "Technologies used",
        "credits_tech_list": ("Python · Tkinter · Pillow · keyboard · Requests · "
                              "PyInstaller · REST APIs (Groq, Gemini, OpenRouter) · "
                              "OpenCode · Antigravity IDE"),
        "credits_created_label": "Creation:",
        "credits_created_value": "March 19, 2026",
        "credits_updated_label": "Last update:",
        "credits_updated_value": "August 23, 2026",
        "credits_close": "Close",
        "toast_title": "🚀 Test Solver AI",
        "toast_msg": "Service running. {hotkey} to analyze.",
        "toast_msg_stopped": "Service stopped. Start it from the main panel.",
        "toast_background": "App stays active in the background. Run the .exe again to reopen the panel.",
        "err_connection": "Connection error. Check your internet.",
        "err_timeout": "Request timed out.",
        "err_invalid_key": "Invalid or empty API key.",
        "success_conn": "✓ Successful connection",
        "analyzing": "Analyzing screen…",
        "calling_api": "Calling API…",
        "overlay_title": "🤖 Test Solver AI",
        "error_title": "⚠️ RUNTIME ERROR",
        "suggestion": "💡 Suggestion:\n",
        "suggestion_msg": "Check the API key and provider connection in settings.",
        "btn_retry": "🔄 Retry",
        "msg_saved": "Settings saved successfully.",
        "msg_hotkey_err": "Error registering hotkeys.",
        "msg_hotkey_invalid": "Invalid hotkeys: they must differ and use a valid format (e.g. f8).",
        "msg_service_started": "Service started successfully.",
        "msg_service_stopped": "Service stopped successfully.",
        "msg_service_err": "Error changing service state.",
        "msg_service_crashed": "The service terminated unexpectedly.",
        "msg_stop_failed": "Could not release the keyboard hooks.",
        "msg_exit_confirm": "Do you really want to exit Test Solver AI?",
        "msg_exit_title": "Exit",
        "banner_no_key_title": "⚠ Your API key is not configured",
        "banner_no_key_msg": "Set up a provider to enable screen analysis.",
        "banner_btn": "Configure now",
        "info_provider": "PROVIDER",
        "info_model": "MODEL",
        "info_language": "LANGUAGE",
        "info_hotkey_analyze": "CAPTURE",
        "info_hotkey_close": "CLOSE APP",
        "uptime_label": "Uptime:",
        "last_check_label": "Last check:",
        "monitor_hint": "Automatic monitoring every second",
        "lang_es": "Español",
        "lang_en": "English"
    }
}


def tr(key):
    lang = config.get("language", "es")
    return TRANSLATIONS.get(lang, TRANSLATIONS["es"]).get(key, key)


# Resolve resource paths
ICON_ICO = get_resource_path("media/test-solver-v1.0.2.ico")
ICON_PNG = get_resource_path("media/test-solver-v1.0.2.png")


# Sanitize keys in error messages so they never leak into logs or dialogs
def sanitize_error(text):
    if not text:
        return text
    text = re.sub(r"gsk_[a-zA-Z0-9]{40,}", "gsk_***[HIDDEN]***", text)
    text = re.sub(r"sk-[a-zA-Z0-9]{40,}", "sk-***[HIDDEN]***", text)
    return text


# Load configuration with backwards compatibility migrations
def load_config():
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
        except Exception:
            pass
        return json.loads(json.dumps(DEFAULT_CONFIG))

    try:
        # utf-8-sig tolerates a BOM left behind by PowerShell/Notepad edits
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            cfg = json.load(f)

            # Migration to nested providers config
            if "providers" not in cfg:
                cfg["providers"] = json.loads(json.dumps(DEFAULT_CONFIG["providers"]))
                if "api_key" in cfg:
                    cfg["providers"]["groq"]["api_key"] = cfg["api_key"]
                if "model" in cfg:
                    cfg["providers"]["groq"]["model"] = cfg["model"]

            # Fill missing keys recursively
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v

            for provider, data in DEFAULT_CONFIG["providers"].items():
                if provider not in cfg["providers"]:
                    cfg["providers"][provider] = data.copy()
                else:
                    for subkey, subval in data.items():
                        if subkey not in cfg["providers"][provider]:
                            cfg["providers"][provider][subkey] = subval

            # Heal configs pointing at models the provider no longer serves
            groq_model = cfg["providers"]["groq"].get("model", "")
            if groq_model in DEPRECATED_GROQ_MODELS:
                cfg["providers"]["groq"]["model"] = \
                    DEFAULT_CONFIG["providers"]["groq"]["model"]
            return cfg
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))


# Save configuration
def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {sanitize_error(str(e))}")


# Helper to compress and convert image to base64
def optimize_image_to_base64(img, quality=85, max_width=1600):
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.convert('RGB').save(buffer, format='JPEG', quality=quality)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


# Fade animations
def fade_in(win, target=0.97, step=0.08):
    if not win.winfo_exists():
        return
    current = float(win.attributes('-alpha'))
    if current < target:
        win.attributes('-alpha', min(current + step, target))
        win.after(15, lambda: fade_in(win, target, step))


def fade_out(win, callback, step=0.08):
    if not win.winfo_exists():
        return
    current = float(win.attributes('-alpha'))
    if current > 0.05:
        win.attributes('-alpha', max(current - step, 0))
        win.after(15, lambda: fade_out(win, callback, step))
    else:
        callback()


def apply_icon(win):
    try:
        if os.path.exists(ICON_ICO):
            win.iconbitmap(ICON_ICO)
    except Exception:
        pass


def center_on_screen(win, w=None, h=None):
    """Center a window; sizes default to its requested geometry."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    ww = min(w if w else win.winfo_reqwidth(), sw - 20)
    wh = min(h if h else win.winfo_reqheight(), sh - 20)
    x = max((sw - ww) // 2, 0)
    y = max((sh - wh) // 2, 0)
    win.geometry(f"{ww}x{wh}+{x}+{y}")


def fmt_uptime(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:d}h {m:02d}m {s:02d}s"
    return f"{m:02d}:{s:02d}"


def fmt_clock(ts):
    if not ts:
        return "-"
    return time.strftime("%H:%M:%S", time.localtime(ts))


# UI pub-sub for service snapshots (thread-safe via the Tk queue)
def subscribe_ui(fn):
    if fn not in _ui_listeners:
        _ui_listeners.append(fn)


def unsubscribe_ui(fn):
    if fn in _ui_listeners:
        _ui_listeners.remove(fn)


# Single instance socket checker
def check_single_instance(root):
    global _instance_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.listen(5)
        _instance_socket = s

        threading.Thread(target=socket_listener, args=(s, root), daemon=True).start()
        return True
    except socket.error:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
            s.sendall(b"show_main")
            s.close()
        except Exception:
            pass
        return False


def socket_listener(sock, root):
    while True:
        try:
            conn, addr = sock.accept()
            data = conn.recv(1024)
            if data == b"show_main":
                _queue.put(('show_main', None))
            elif data == b"show_settings":
                _queue.put(('show_settings', None))
            conn.close()
        except Exception:
            break


# Extensible Provider Architecture
# ----------------------------------------------------------------------------
# Every provider is a small adapter exposing four operations:
#   get_url(base_url) -> endpoint that receives the POST
#   get_headers(api_key) -> auth/content headers
#   get_payload(model, image_b64, prompt_lang) -> request body
#   parse_response(response_json) -> final answer text
# plus METADATA used by the UI: label, free tier, vision support, key policy
# and a limitation note (translation key). Adding a new provider means adding
# one small subclass + one registry entry; no core logic changes required.
# ----------------------------------------------------------------------------
def _exam_prompt(prompt_lang):
    if prompt_lang == "en":
        return (
            "You are an expert exam-solving assistant. Carefully analyze the screen image and identify all the questions present.\n"
            "Support all question types: single choice, multiple choice, true/false, or fill-in-the-blanks.\n"
            "For each identified question:\n"
            "1) State the question text and its options.\n"
            "2) Write the correct answer or answers in bold (e.g., 'The correct answer is **b. ...**' or '**True**').\n"
            "3) Explain concisely but rigorously why this is the correct answer.\n"
            "Respond in structured English using basic Markdown. Be direct and avoid unnecessary intros."
        )
    return (
        "Eres un asistente experto en resolución de exámenes. Analiza detenidamente la imagen de la pantalla e identifica todas las preguntas que aparezcan.\n"
        "Soporta todo tipo de preguntas: selección única, selección múltiple, verdadero/falso o rellenar huecos.\n"
        "Para cada pregunta identificada:\n"
        "1) Indica el enunciado de la pregunta y sus opciones.\n"
        "2) Escribe la respuesta o respuestas correctas en negrita (ej. 'La respuesta correcta es **b. ...**' o '**Verdadero**').\n"
        "3) Explica de forma concisa pero rigurosa por qué es la respuesta correcta.\n"
        "Responde en español estructurado utilizando Markdown básico. Sé directo y evita preámbulos innecesarios."
    )


def _strip_think(text):
    """Remove reasoning-model chain-of-thought blocks from an answer."""
    while True:
        start = text.find('<think>')
        if start == -1:
            break
        end = text.find('</think>', start)
        text = (text[:start] +
                (text[end + len('</think>'):] if end != -1 else ""))
    return text.strip()


class BaseProvider:
    # ---- metadata (overridden by each provider) ----
    id = "custom"
    label = "Custom"
    free = None             # True = free, False = paid, "tier" = free level
    requires_key = True
    vision = False          # supports image input?
    note_key = "prov_note_custom"   # translation key for the limits note

    def get_url(self, base_url):
        raise NotImplementedError

    def endpoint(self, base_url, model):
        """Final POST URL; defaults ignore the model (OpenAI-style)."""
        return self.get_url(base_url)

    def ui_label(self):
        """Localized display name for the settings combobox."""
        return TRANSLATIONS.get(config.get("language", "es"),
                                TRANSLATIONS["es"]).get(
            f"prov_label_{self.id}", self.label)

    def ping_payload(self, model):
        """Minimal cheap body used by the 'Test connection' button."""
        return {
            'model': model,
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'max_tokens': 5
        }

    def get_headers(self, api_key):
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        return headers

    def get_payload(self, model, image_b64, prompt_lang):
        return {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_b64}'
                            }
                        },
                        {
                            'type': 'text',
                            'text': _exam_prompt(prompt_lang)
                        }
                    ]
                }
            ],
            'max_tokens': 2000
        }

    def parse_response(self, response_json):
        if 'choices' not in response_json or len(response_json['choices']) == 0:
            raise Exception("No choices found in API response")
        content = response_json['choices'][0]['message']['content'] or ""
        return _strip_think(content)


class OpenAICompatProvider(BaseProvider):
    """Any OpenAI-style /chat/completions endpoint with configurable defaults."""

    default_base = ""

    def get_url(self, base_url):
        url = base_url or self.default_base
        if not url:
            raise ValueError("Base URL must be configured.")
        if url.endswith("/chat/completions"):
            return url
        return url.rstrip('/') + "/chat/completions"

    def endpoint(self, base_url, model):
        return self.get_url(base_url)


class GroqProvider(OpenAICompatProvider):
    id = "groq"
    label = "Groq"
    free = True
    requires_key = True
    vision = True
    note_key = "prov_note_groq"
    models = ["qwen/qwen3.6-27b", "openai/gpt-oss-120b",
              "openai/gpt-oss-20b", "groq/compound-mini"]
    default_base = "https://api.groq.com/openai/v1"


class GeminiProvider(BaseProvider):
    """Google AI Studio (generativelanguage) native REST adapter."""

    id = "gemini"
    label = "Google Gemini"
    free = "tier"
    requires_key = True
    vision = True
    note_key = "prov_note_gemini"
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite",
              "gemini-3-flash", "gemini-3.1-flash-lite"]
    default_base = "https://generativelanguage.googleapis.com/v1beta"

    def get_url(self, base_url):
        base = (base_url or self.default_base).rstrip('/')
        return base

    def endpoint(self, base_url, model):
        base = (base_url or self.default_base).rstrip('/')
        if not base:
            raise ValueError("Base URL must be configured.")
        safe_model = requests.utils.quote(model or "gemini-2.5-flash",
                                          safe='')
        return f"{base}/models/{safe_model}:generateContent"

    def get_headers(self, api_key):
        return {'Content-Type': 'application/json', 'x-goog-api-key': api_key}

    def ping_payload(self, model):
        return {
            'contents': [{'parts': [{'text': 'Hi'}]}],
            'generationConfig': {'maxOutputTokens': 5}
        }

    def get_payload(self, model, image_b64, prompt_lang):
        return {
            'contents': [
                {
                    'parts': [
                        {
                            'inline_data': {
                                'mime_type': 'image/jpeg',
                                'data': image_b64
                            }
                        },
                        {'text': _exam_prompt(prompt_lang)}
                    ]
                }
            ],
            'generationConfig': {'maxOutputTokens': 2048}
        }

    def parse_response(self, response_json):
        err = response_json.get('error')
        if err:
            raise Exception(err.get('message', 'Unknown Gemini error'))
        candidates = response_json.get('candidates') or []
        if not candidates:
            raise Exception("No candidates found in Gemini response")
        parts = ((candidates[0].get('content') or {}).get('parts')) or []
        texts = [p.get('text', '') for p in parts
                 if isinstance(p, dict) and p.get('text')
                 and not p.get('thought')]
        answer = "".join(texts).strip()
        if not answer:
            raise Exception("Gemini returned an empty response")
        return _strip_think(answer)


class OpenRouterProvider(OpenAICompatProvider):
    id = "openrouter"
    label = "OpenRouter"
    free = "tier"
    requires_key = True
    vision = True      # depends on the chosen model (free vision ids below)
    note_key = "prov_note_openrouter"
    models = ["google/gemma-4-31b-it:free",
              "google/gemma-4-26b-a4b-it:free",
              "nvidia/nemotron-nano-12b-v2-vl:free",
              "nvidia/nemotron-3-ultra-550b-a55b:free",
              "xiaomi/mimo-v2-flash:free",
              "tencent/hy3:free",
              "deepseek/deepseek-chat-v3-0324:free",
              "openai/gpt-oss-20b:free"]
    default_base = "https://openrouter.ai/api/v1"

    def get_headers(self, api_key):
        headers = super().get_headers(api_key)
        headers.setdefault("HTTP-Referer", "https://github.com/ronnyfeliz")
        headers.setdefault("X-Title", "Test Solver AI")
        return headers


class DeepSeekProvider(OpenAICompatProvider):
    id = "deepseek"
    label = "DeepSeek"
    free = False
    requires_key = True
    vision = False     # chat/reasoner are text-only
    note_key = "prov_note_deepseek"
    models = ["deepseek-chat", "deepseek-reasoner"]
    default_base = "https://api.deepseek.com/v1"


class OpenCodeZenProvider(OpenAICompatProvider):
    id = "opencode"
    label = "Big Pickle (OpenCode Zen)"
    free = True
    requires_key = True
    vision = False     # stealth coding model: text only
    note_key = "prov_note_opencode"
    models = ["big-pickle"]
    default_base = "https://opencode.ai/zen/v1"


class OpenAIProvider(OpenAICompatProvider):
    id = "openai"
    label = "OpenAI"
    free = False
    requires_key = True
    vision = True
    note_key = "prov_note_openai"
    models = ["gpt-4o-mini", "gpt-4o"]
    default_base = "https://api.openai.com/v1"


class CustomProvider(OpenAICompatProvider):
    id = "custom"
    label = "Personalizado"
    free = None
    requires_key = False
    vision = True      # unknown endpoint; assume it can handle images
    note_key = "prov_note_custom"
    models = []
    default_base = ""


# Single source of truth for provider adapters. To add a provider: subclass,
# fill metadata and register it here. The UI, persistence and analysis flow
# pick it up automatically.
PROVIDERS = {
    p.id: p for p in (
        GroqProvider(),
        GeminiProvider(),
        OpenRouterProvider(),
        DeepSeekProvider(),
        OpenCodeZenProvider(),
        OpenAIProvider(),
        CustomProvider(),
    )
}

PROVIDER_ORDER = ["groq", "gemini", "openrouter", "opencode", "deepseek",
                  "openai", "custom"]

# Curated model suggestions per provider (the field stays editable so any
# valid model id can be typed manually).
PROVIDER_MODELS = {
    "groq": [
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound-mini",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash",
        "gemini-3.1-flash-lite",
    ],
    "openrouter": [
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "xiaomi/mimo-v2-flash:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "openai/gpt-oss-20b:free",
    ],
    "opencode": ["big-pickle"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "custom": [],
}


def provider_note(pid):
    """Localized informational note for a provider ('' when none)."""
    return TRANSLATIONS.get(config.get("language", "es"),
                            TRANSLATIONS["es"]).get(f"prov_note_{pid}", "")


def provider_badges(pid):
    """Human-readable badges for a provider: pricing · vision · key policy."""
    meta = PROVIDERS.get(pid)
    if meta is None:
        return ""
    if meta.free is True:
        price = tr("prov_free")
    elif meta.free == "tier":
        price = tr("prov_freemium")
    elif meta.free is False:
        price = tr("prov_paid")
    else:
        price = tr("prov_depends")
    vision = tr("prov_vision") if meta.vision else tr("prov_text_only")
    keypol = "" if meta.requires_key else f" · {tr('prov_no_key')}"
    return f"{price} · {vision}{keypol}"

# ============================================================================
# SERVICE CONTROLLER - single source of truth based on REAL service state
# ----------------------------------------------------------------------------
# The "service" is the live global-hotkey listener. Its true state is probed
# from the keyboard library's actual structures (armed hotkey tables plus the
# alive status of the low-level OS hook thread). No internal boolean flag is
# ever trusted on its own. States: stopped / starting / running / stopping /
# crashed (terminated unexpectedly) + sanitized error details.
# ============================================================================
STATE_STOPPED = "stopped"
STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPING = "stopping"
STATE_CRASHED = "crashed"

WM_QUIT = 0x0012


class ServiceController:
    POLL_SECONDS = 1.0

    def __init__(self):
        self.state = STATE_STOPPED
        self.detail = None        # sanitized human-readable detail (errors)
        self.failed_op = None     # 'start' | 'stop' | None (UI error flash)
        self.started_at = None
        self.last_check = None
        self._op_lock = threading.RLock()
        self._wd_stop = threading.Event()
        self._wd_thread = None

    # ------------------------- REAL STATE PROBING -------------------------
    @staticmethod
    def _listener():
        return getattr(keyboard, "_listener", None)

    @classmethod
    def active_hotkey_count(cls):
        """Number of hotkey bindings REALLY armed in the listener tables."""
        lst = cls._listener()
        if lst is None:
            return 0
        n = 0
        for attr in ("nonblocking_hotkeys", "blocking_hotkeys"):
            table = getattr(lst, attr, None)
            if table:
                try:
                    n += sum(len(v) for v in table.values())
                except Exception:
                    pass
        return n

    @classmethod
    def probe_real(cls):
        """True ONLY if hooks are truly armed AND the OS listener thread lives."""
        lst = cls._listener()
        if lst is None:
            return False
        lt = getattr(lst, "listening_thread", None)
        pt = getattr(lst, "processing_thread", None)
        if cls.active_hotkey_count() <= 0:
            return False
        if lt is None or not lt.is_alive():
            return False
        if pt is not None and not pt.is_alive():
            return False
        return True

    def snapshot(self):
        uptime = None
        if self.state == STATE_RUNNING and self.started_at:
            uptime = int(time.time() - self.started_at)
        return {
            "state": self.state,
            "detail": self.detail,
            "failed_op": self.failed_op,
            "uptime": uptime,
            "last_check": self.last_check
        }

    def publish(self, tick=False):
        _queue.put(("service_tick" if tick else "service_state", self.snapshot()))

    def refresh_initial(self):
        """Startup truth-check: NEVER trust defaults, probe the real world."""
        self.last_check = time.time()
        if self.probe_real():
            self.state = STATE_RUNNING
            self.started_at = self.started_at or time.time()
        else:
            self.state = STATE_STOPPED
            self.started_at = None
        self.detail = None
        self.publish()

    # --------------------------- HOOK TEARDOWN ----------------------------
    def teardown_hooks(self):
        """
        Fully release the OS-level keyboard hook and stop the listener thread
        so nothing keeps working after Stop (no residual hooks/threads).
        Returns an error string when the thread could not be confirmed dead.
        """
        try:
            keyboard.remove_all_hotkeys()
        except Exception:
            pass
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            keyboard._hotkeys.clear()
        except Exception:
            pass

        err = None
        lst = self._listener()
        lt = getattr(lst, "listening_thread", None) if lst else None
        if lt is not None and lt.is_alive() and lt.ident:
            user32 = ctypes.windll.user32
            posted = user32.PostThreadMessageW(lt.ident, WM_QUIT, 0, 0)
            # Silence the benign OSError the keyboard lib prints while its
            # GetMessage loop unwinds after our controlled WM_QUIT.
            prev_hook = threading.excepthook
            threading.excepthook = lambda args: None
            try:
                lt.join(timeout=3)
            finally:
                threading.excepthook = prev_hook
            if lt.is_alive() or not posted:
                err = tr("msg_stop_failed")

        if lst is not None:
            try:
                lst.listening = False  # let add_hotkey spin a fresh listener
            except Exception:
                pass
        return err

    # ------------------------------ START ---------------------------------
    def start(self):
        """Request service start. Returns True when a start was initiated."""
        with self._op_lock:
            if self.probe_real():
                # Reality check: already truly running -> reconcile, no dup
                if self.state != STATE_RUNNING:
                    self.state = STATE_RUNNING
                    self.started_at = self.started_at or time.time()
                    self.detail = None
                    self.publish()
                return False
            if self.state in (STATE_STARTING, STATE_STOPPING):
                return False
            self.state = STATE_STARTING
            self.detail = None
            self.failed_op = None
            self.started_at = None
            self.last_check = time.time()
            self.publish()
        threading.Thread(target=self._do_start, daemon=True,
                         name="svc-start").start()
        return True

    def _do_start(self):
        try:
            self.teardown_hooks()  # clear any stale remnants before arming
            hk_a = (config.get("hotkey_analyze") or "").strip().lower()
            hk_c = (config.get("hotkey_close") or "").strip().lower()
            if not hk_a or not hk_c or hk_a == hk_c:
                raise ValueError(tr("msg_hotkey_invalid"))
            keyboard.parse_hotkey(hk_a)  # raises on invalid syntax
            keyboard.parse_hotkey(hk_c)

            keyboard.add_hotkey(hk_a, self._on_analyze_hotkey)
            keyboard.add_hotkey(hk_c, self._on_quit_hotkey)
            time.sleep(0.25)  # give the OS hook thread time to arm
            if not self.probe_real():
                raise RuntimeError(tr("msg_hotkey_err"))

            self._watchdog_start()
            self.state = STATE_RUNNING
            self.started_at = time.time()
            self.last_check = time.time()
            self.detail = None
            self.failed_op = None
            self.publish()
            _queue.put(("toast", (tr("toast_title"), tr("msg_service_started"))))
        except Exception as e:
            try:
                self.teardown_hooks()
            except Exception:
                pass
            err_text = sanitize_error(str(e)) or tr("msg_service_err")
            self.state = STATE_STOPPED
            self.detail = err_text
            self.failed_op = "start"
            self.started_at = None
            self.last_check = time.time()
            self.publish()
            _queue.put(("toast", (tr("toast_title"),
                                  f"{tr('msg_service_err')}: {err_text}")))

    # ------------------------------- STOP ----------------------------------
    def stop(self, wait=False):
        """Request service stop. wait=True blocks until verified (exit path)."""
        with self._op_lock:
            # If a start is still settling, give it a moment so Stop always
            # acts on the final state instead of being refused mid-transition.
            if self.state == STATE_STARTING:
                deadline = time.time() + 2.5
                while self.state == STATE_STARTING and time.time() < deadline:
                    self._op_lock.release()
                    time.sleep(0.05)
                    self._op_lock.acquire()
            if self.state in (STATE_STOPPED, STATE_CRASHED) and not self.probe_real():
                return False
            if self.state in (STATE_STARTING, STATE_STOPPING) and not wait:
                return False
            self.state = STATE_STOPPING
            self.detail = None
            self.failed_op = None
            self.last_check = time.time()
            self.publish()
            if wait:
                self._do_stop()
                return True
        threading.Thread(target=self._do_stop, daemon=True,
                         name="svc-stop").start()
        return True

    def _do_stop(self):
        try:
            err = self.teardown_hooks()
            self._watchdog_halt()

            still_armed = self.active_hotkey_count() > 0
            if still_armed:
                # Could not remove the hooks: reflect TRUE state (still running)
                self.state = STATE_RUNNING
                self.detail = sanitize_error(err) if err else tr("msg_stop_failed")
                self.failed_op = "stop"
                self.last_check = time.time()
                self.publish()
                _queue.put(("toast", (tr("toast_title"),
                                      f"{tr('msg_service_err')}: {self.detail}")))
                return

            self.state = STATE_STOPPED
            self.started_at = None
            self.detail = None
            self.failed_op = None
            self.last_check = time.time()
            self.publish()
            _queue.put(("toast", (tr("toast_title"), tr("msg_service_stopped"))))
        except Exception as e:
            err_text = sanitize_error(str(e)) or tr("msg_service_err")
            self.state = STATE_RUNNING if self.probe_real() else STATE_STOPPED
            self.detail = err_text
            self.failed_op = "stop"
            self.last_check = time.time()
            self.publish()
            _queue.put(("toast", (tr("toast_title"),
                                  f"{tr('msg_service_err')}: {err_text}")))

    # ---------------------------- RELOAD HOTKEYS ---------------------------
    def reload_hotkeys(self):
        """Re-arm hooks with freshly saved config while staying truthful."""

        def job():
            with self._op_lock:
                self.state = STATE_STOPPING
                self.detail = None
                self.publish()
                try:
                    self.teardown_hooks()
                    self._watchdog_halt()
                except Exception:
                    pass
            self._do_start()
        threading.Thread(target=job, daemon=True, name="svc-reload").start()

    # ------------------------------ WATCHDOG --------------------------------
    def _watchdog_start(self):
        self._wd_stop.clear()
        if self._wd_thread is not None and self._wd_thread.is_alive():
            return
        self._wd_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="svc-watchdog")
        self._wd_thread.start()

    def _watchdog_halt(self):
        self._wd_stop.set()
        if self._wd_thread is not None:
            self._wd_thread.join(timeout=2)
        self._wd_thread = None

    def _watchdog_loop(self):
        """Every second compare expected state vs REAL state of the service."""
        while not self._wd_stop.wait(self.POLL_SECONDS):
            try:
                self.last_check = time.time()
                alive = self.probe_real()

                if self.state == STATE_RUNNING and not alive:
                    # Unexpected termination detected outside the UI
                    try:
                        self.teardown_hooks()
                    except Exception:
                        pass
                    self.state = STATE_CRASHED
                    self.detail = tr("msg_service_crashed")
                    self.failed_op = None
                    self.started_at = None
                    self.publish()
                    _queue.put(("toast", (tr("toast_title"),
                                          tr("msg_service_crashed"))))
                    continue

                if self.state == STATE_CRASHED and alive:
                    # Hooks came back externally: reconcile with reality
                    self.state = STATE_RUNNING
                    self.started_at = self.started_at or time.time()
                    self.detail = None
                    self.publish()
                    continue

                self.publish(tick=True)  # refresh uptime / last-check labels
            except Exception:
                pass

    # --------------------------- HOTKEY CALLBACKS ---------------------------
    def _on_analyze_hotkey(self):
        try:
            _queue.put(('init_loading', None))
            start_vision_analysis()
        except Exception as e:
            _queue.put(("toast", (tr("toast_title"), sanitize_error(str(e)))))

    def _on_quit_hotkey(self):
        _queue.put(('request_quit', None))

# ============================================================================
# WIDGETS
# ============================================================================
class RoundedButton(tk.Canvas):
    """Modern flat button with ROUNDED CORNERS drawn on a Canvas.

    Supports the full state set: normal / hover / pressed / disabled plus an
    error flash. Keeps a tk.Button-like API subset used across the app:
    config(text=|bg=|fg=|state=), cget('text'), set_enabled(), enabled(),
    flash_error().
    """

    CORNER_RADIUS = 10

    def __init__(self, master, palette="surface", command=None, text="",
                 font=None, padx=12, pady=6, **kw):
        self.p = BTN_PALETTES.get(palette, BTN_PALETTES["surface"])
        self._command = command
        self._fontobj = tkfont.Font(font=font) if font else tkfont.Font(
            family=FONT_FAMILY, size=9)
        self._padx = padx
        self._pady = pady
        self._hover = False
        self._pressed = False
        self._flash_job = None
        self._bg_override = None
        self._fg_override = None
        w = self._fontobj.measure(text) + 2 * padx + 4
        h = self._fontobj.metrics("linespace") + 2 * pady + 2
        try:
            parent_bg = master.cget("bg")
        except Exception:
            parent_bg = COLORS["bg"]
        super().__init__(master, width=w, height=h, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = text
        self._draw()

        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        # Redraw when a layout manager stretches/shrinks us (grid sticky=ew)
        self.bind("<Configure>", lambda _e: self._draw(), add="+")

    # ------------------------------ geometry --------------------------------
    def _radius(self):
        return max(4, min(self.CORNER_RADIUS,
                          max(self.winfo_width(),
                              self.winfo_reqwidth()) // 2 - 1,
                          max(self.winfo_height(),
                              self.winfo_reqheight()) // 2 - 1))

    def _round_rect(self, x1, y1, x2, y2, r):
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                  x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                  x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(points, smooth=True)

    # ------------------------------- colors ---------------------------------
    def _colors(self):
        if not self.enabled():
            return BTN_DISABLED_BG, BTN_DISABLED_FG
        if self._flash_job is not None:
            return "#ff5c61", "#ffffff"
        bg = self._bg_override or (
            self.p["press"] if self._pressed else
            self.p["hover"] if self._hover else self.p["bg"])
        fg = self._fg_override or (
            self.p.get("hover_fg", self.p.get("fg", COLORS["text"]))
            if (self._hover or self._pressed) else
            self.p.get("fg", COLORS["text"]))
        return bg, fg

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = self.winfo_reqwidth()
        if h <= 1:
            h = self.winfo_reqheight()
        bg, fg = self._colors()
        r = self._radius()
        rect = self._round_rect(1, 1, w - 2, h - 2, r)
        self.itemconfig(rect, fill=bg, outline="")
        self._txt_item = self.create_text(w // 2, h // 2, text=self._text,
                                          font=self._fontobj, fill=fg)

    # ------------------------------ behaviour -------------------------------
    def enabled(self):
        return getattr(self, "_enabled", True)

    def set_enabled(self, value):
        self._enabled = bool(value)
        self.configure(cursor="hand2" if value else "arrow")
        self._draw()

    def _on_enter(self, _e):
        self._hover = True
        if self.enabled():
            self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._pressed = False
        if self.enabled():
            self._draw()

    def _on_press(self, _e):
        if not self.enabled():
            return
        self._pressed = True
        self._draw()

    def _on_release(self, _e):
        if not self.enabled():
            return
        was_pressed = self._pressed
        x, y = self.winfo_pointerxy()
        inside = (self.winfo_rootx() <= x < self.winfo_rootx() +
                  self.winfo_width()
                  and self.winfo_rooty() <= y < self.winfo_rooty() +
                  self.winfo_height())
        self._pressed = False
        self._draw()
        if was_pressed and inside and self._command:
            self._command()

    def invoke(self):
        """tk.Button-compatible programmatic click (used by tests)."""
        if self.enabled() and self._command:
            self._command()

    def flash_error(self):
        """Visual error feedback on the exact button whose action failed."""
        if self._flash_job is not None:
            try:
                self.after_cancel(self._flash_job)
            except Exception:
                pass
        self._flash_job = self.after(
            BTN_ERROR_FLASH_MS, self._end_flash)
        self._draw()

    def _end_flash(self):
        self._flash_job = None
        self._draw()

    # --------------------- tk.Button-compatible surface ---------------------
    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return "normal" if self.enabled() else "disabled"
        if key == "bg":
            return self._colors()[0]
        if key == "font":
            # Named-font handle so callers can re-wrap it in tkfont.Font().
            return self._fontobj.name
        return super().cget(key)

    def config(self, **kw):
        redraw = False
        if "text" in kw:
            new_text = str(kw.pop("text"))
            if new_text != self._text:
                self._text = new_text
                w = self._fontobj.measure(self._text) + 2 * self._padx + 4
                super().configure(width=w)
                redraw = True
        if "bg" in kw:
            self._bg_override = kw.pop("bg")
            redraw = True
        if "fg" in kw:
            self._fg_override = kw.pop("fg")
            redraw = True
        if "state" in kw:
            state = str(kw.pop("state"))
            self.set_enabled(state != "disabled")
        if "command" in kw:
            self._command = kw.pop("command")
        if kw:
            super().config(**kw)
        if redraw:
            self._draw()

    configure = config


class StatusDot(tk.Canvas):
    """Round status indicator with pulse animation for transitional states."""

    STATE_COLORS = {
        STATE_RUNNING: COLORS["green"],
        STATE_STOPPED: COLORS["muted"],
        STATE_STARTING: COLORS["yellow"],
        STATE_STOPPING: COLORS["orange"],
        STATE_CRASHED: COLORS["red"]
    }
    PULSE_STATES = (STATE_STARTING, STATE_STOPPING)

    def __init__(self, master, diameter=12, bg=None, **kw):
        super().__init__(master, width=diameter, height=diameter,
                         bg=bg or COLORS["bg"], highlightthickness=0, bd=0)
        self.d = diameter
        self._state = STATE_STOPPED
        self._pulse_job = None
        self._pulse_on = True
        self.draw()

    def set_state(self, state):
        if state != self._state:
            self._state = state
            self._pulse_on = True
            self._cancel_pulse()
        self.draw()
        if state in self.PULSE_STATES:
            self._schedule_pulse()

    def _cancel_pulse(self):
        if self._pulse_job is not None:
            try:
                self.after_cancel(self._pulse_job)
            except Exception:
                pass
            self._pulse_job = None

    def _schedule_pulse(self):
        self._pulse_job = self.after(500, self._pulse_tick)

    def _pulse_tick(self):
        if self._state not in self.PULSE_STATES or not self.winfo_exists():
            self._pulse_job = None
            return
        self._pulse_on = not self._pulse_on
        self.draw()
        self._schedule_pulse()

    def draw(self):
        self.delete("all")
        color = self.STATE_COLORS.get(self._state, COLORS["muted"])
        if self._state in self.PULSE_STATES and not self._pulse_on:
            color = COLORS["border"]
        pad = 2
        self.create_oval(pad, pad, self.d - pad, self.d - pad,
                         fill=color, outline="")


class ScrollFrame(tk.Frame):
    """Responsive vertical-scroll container so content is never cut off."""

    def __init__(self, master, bg=None, max_height=None, **kw):
        bg = bg or COLORS["bg"]
        super().__init__(master, bg=bg, **kw)
        self.max_height = max_height

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                width=10, troughcolor=bg, bg=COLORS["surface"],
                                activebackground=COLORS["surface_hi"])
        self.canvas.configure(yscrollcommand=self.vsb.set)
        # The scrollbar stays UNPACKED until content actually overflows
        # (_update_scrollbar decides), so short pages show no scrollbar.
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Mouse-wheel scrolling while the pointer is over this container
        self.bind("<Enter>", self._bind_wheel, add="+")
        self.bind("<Leave>", self._unbind_wheel, add="+")

    def _on_inner_configure(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_scroll_width()
        self._update_scrollbar()

    def _on_canvas_configure(self, e):
        self.canvas.itemconfigure(self._win_id, width=e.width)
        self._update_scrollbar()

    def _update_scrollbar(self):
        """Show the scrollbar ONLY when content actually overflows."""
        try:
            inner_h = self.inner.winfo_reqheight()
            canvas_h = self.canvas.winfo_height()
        except Exception:
            return
        scrollable = canvas_h > 20 and inner_h > canvas_h + 2
        if scrollable and not self.vsb.winfo_manager():
            self.vsb.pack(side="right", fill="y", before=self.canvas)
        elif not scrollable and self.vsb.winfo_manager():
            self.vsb.pack_forget()

    def _sync_scroll_width(self):
        try:
            self.canvas.itemconfigure(self._win_id,
                                      width=self.canvas.winfo_width())
        except Exception:
            pass

    def _bind_wheel(self, _e):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _unbind_wheel(self, _e):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _on_wheel(self, e):
        if not self.vsb.winfo_manager():
            return
        step = int(-1 * (e.delta / 120) * 40)
        self.canvas.yview_scroll(step, "units")

    def content_height(self):
        self.update_idletasks()
        return max(self.inner.winfo_reqheight(), 1)


# Toast Notification
class ToastNotification(tk.Toplevel):
    def __init__(self, root, title, message, duration=4200):
        super().__init__(root)
        self.root = root
        self.duration = duration

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.0)
        apply_icon(self)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = max(320, min(460, 90 + len(message) * 6))
        h = 84
        x = sw - w - 24
        y = sh - h - 56
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=COLORS["border"])

        container = tk.Frame(self, bg=COLORS["panel"],
                             highlightbackground=COLORS["border"],
                             highlightthickness=1)
        container.place(x=1, y=1, relwidth=1.0, relheight=-2 / h if h > 100 else 1.0,
                        relx=0, rely=0)

        accent = tk.Frame(container, width=4, bg=COLORS["accent"])
        accent.place(x=0, y=0, relheight=1.0)

        lbl_title = tk.Label(container, text=title, font=font(10, "bold"),
                             bg=COLORS["panel"], fg=COLORS["accent"], anchor="w")
        lbl_title.place(x=14, y=10, relwidth=1.0)

        lbl_msg = tk.Label(container, text=message, font=font(9),
                           bg=COLORS["panel"], fg=COLORS["text"],
                           justify='left', wraplength=w - 40, anchor="w")
        lbl_msg.place(x=14, y=34, relwidth=1.0)

        for widget in (container, lbl_title, lbl_msg):
            widget.bind("<Double-Button-1>", lambda e: self.open_settings())

        fade_in(self, target=0.97)
        self.after(self.duration, self.dismiss)

    def open_settings(self):
        _queue.put(('show_settings', None))
        self.dismiss()

    def dismiss(self):
        fade_out(self, self.destroy)


def show_toast(root, title, message):
    ToastNotification(root, title, message)


def open_main_window(root):
    """Open (or restore/focus) the main control panel window."""
    global _main_window
    if _main_window is not None and _main_window.winfo_exists():
        _main_window.deiconify()
        _main_window.lift()
        _main_window.focus_force()
        return _main_window
    _main_window = MainWindow(root)
    return _main_window


# Collaborator Credits Modal
class CreditsModal(tk.Toplevel):
    GITHUB_URL = "https://github.com/ronnyfeliz"
    WIDTH = 430

    def __init__(self, parent):
        super().__init__(parent)
        self.title(tr("btn_credits"))
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.attributes("-topmost", True)
        apply_icon(self)

        self.transient(parent)
        self.grab_set()
        self._build()
        # Never taller than the work area: the inner ScrollFrame handles
        # overflow so every credit section is reachable.
        self.update_idletasks()
        screen_h = self.winfo_screenheight()
        max_h = max(screen_h - 160, 320)
        req_h = self.winfo_reqheight()
        final_h = min(req_h + 8, max_h)
        center_on_screen(self, self.WIDTH, final_h)
        self.lift()

    def _build(self):
        outer = tk.Frame(self, bg=COLORS["bg"], padx=20, pady=14)
        outer.pack(fill='both', expand=True)

        tk.Label(outer, text=tr("credits_title"), font=font(13, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(anchor='center')
        tk.Frame(outer, height=1, bg=COLORS["border"]).pack(
            fill='x', pady=(8, 10))

        body = ScrollFrame(outer, bg=COLORS["bg"],
                           max_height=self.winfo_screenheight() - 260)
        body.pack(fill='both', expand=True)
        content = body.inner

        def card(parent):
            c = tk.Frame(parent, bg=COLORS["panel"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1)
            c.pack(fill='x', pady=(0, 10))
            i = tk.Frame(c, bg=COLORS["panel"], padx=14, pady=12)
            i.pack(fill='both', expand=True)
            return i

        # --- 1) Original author & creator: Alex Hatton ---
        author = card(content)
        tk.Label(author, text=tr("credits_author_label"), font=font(8),
                 bg=COLORS["panel"], fg=COLORS["teal"]).pack(anchor='w')
        tk.Label(author, text=tr("credits_author_name"),
                 font=font(12, "bold"), bg=COLORS["panel"],
                 fg=COLORS["text"]).pack(anchor='w', pady=(2, 3))
        tk.Label(author, text=tr("credits_author_desc"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"],
                 justify='left', wraplength=340).pack(anchor='w')

        # --- 2) GUI collaborator: Ronny Feliz ---
        collab = card(content)
        tk.Label(collab, text=tr("credits_collab_label"), font=font(8),
                 bg=COLORS["panel"], fg=COLORS["teal"]).pack(anchor='w')
        tk.Label(collab, text=tr("credits_collab_name"),
                 font=font(12, "bold"), bg=COLORS["panel"],
                 fg=COLORS["text"]).pack(anchor='w', pady=(2, 3))
        tk.Label(collab, text=tr("credits_collab_desc"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"],
                 justify='left', wraplength=340).pack(anchor='w')
        link = tk.Label(collab, text=self.GITHUB_URL,
                        font=font(9, underline=True),
                        bg=COLORS["panel"], fg=COLORS["accent"],
                        cursor="hand2")
        link.pack(anchor='w', pady=(5, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(self.GITHUB_URL))

        # --- 3) Technologies used (real stack only) ---
        tech = card(content)
        tk.Label(tech, text=tr("credits_tech_title"), font=font(10, "bold"),
                 bg=COLORS["panel"], fg=COLORS["accent"]).pack(anchor='w',
                                                               pady=(0, 4))
        for item in tr("credits_tech_list").split("·"):
            row = tk.Frame(tech, bg=COLORS["panel"])
            row.pack(anchor='w', pady=1)
            tk.Label(row, text="•", font=font(9), bg=COLORS["panel"],
                     fg=COLORS["teal"]).pack(side='left', padx=(0, 6))
            tk.Label(row, text=item.strip(), font=font(9),
                     bg=COLORS["panel"], fg=COLORS["subtext"]).pack(side='left')

        # --- 4) Project dates ---
        dates = card(content)
        row_c = tk.Frame(dates, bg=COLORS["panel"])
        row_c.pack(anchor='w', pady=2)
        tk.Label(row_c, text="🗓", font=font(10), bg=COLORS["panel"],
                 fg=COLORS["teal"]).pack(side='left', padx=(0, 8))
        tk.Label(row_c, text=tr("credits_created_label"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"]).pack(side='left')
        tk.Label(row_c, text=tr("credits_created_value"),
                 font=font(9, "bold"), bg=COLORS["panel"],
                 fg=COLORS["text"]).pack(side='left', padx=(6, 0))

        row_u = tk.Frame(dates, bg=COLORS["panel"])
        row_u.pack(anchor='w', pady=2)
        tk.Label(row_u, text="🛠", font=font(10), bg=COLORS["panel"],
                 fg=COLORS["orange"]).pack(side='left', padx=(0, 8))
        tk.Label(row_u, text=tr("credits_updated_label"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"]).pack(side='left')
        tk.Label(row_u, text=tr("credits_updated_value"),
                 font=font(9, "bold"), bg=COLORS["panel"],
                 fg=COLORS["text"]).pack(side='left', padx=(6, 0))

        # --- Version badge (monospace exception: technical token) ---
        tk.Label(content, text=f"Test Solver {TEST_SOLVER_VERSION}",
                 font=font(8, mono=True), bg=COLORS["bg"],
                 fg=COLORS["muted"]).pack(pady=(2, 6))

        RoundedButton(outer, palette="accent", text=tr("credits_close"),
                      command=self.cerrar, font=font(9, "bold"),
                      padx=22, pady=5).pack(anchor='center', pady=(8, 0))

    def cerrar(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


# ============================================================================
# MAIN WINDOW - service control dashboard (opened when the exe starts)
# ============================================================================
def _status_display(state):
    return {
        STATE_RUNNING: (tr("status_running"), COLORS["green"]),
        STATE_STOPPED: (tr("status_stopped"), COLORS["muted"]),
        STATE_STARTING: (tr("status_starting"), COLORS["yellow"]),
        STATE_STOPPING: (tr("status_stopping"), COLORS["orange"]),
        STATE_CRASHED: (tr("status_crashed"), COLORS["red"])
    }.get(state, (tr("status_stopped"), COLORS["muted"]))


class MainWindow(tk.Toplevel):
    WIDTH = 480

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self._flash_jobs = []
        self.title(f"{tr('app_title')} - {TEST_SOLVER_VERSION}")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        apply_icon(self)

        screen_h = self.winfo_screenheight()
        # Chrome (title bar + header + footer) measures ~215 px on Windows;
        # sizing the body with this budget lets the dashboard fit WITHOUT
        # a scrollbar on common 1366x768 screens.
        max_body_h = max(screen_h - 240, 260)

        # ---- Header ----
        header = tk.Frame(self, bg=COLORS["header"], padx=16, pady=12)
        header.pack(fill='x', side='top')

        head_row = tk.Frame(header, bg=COLORS["header"])
        head_row.pack(fill='x')
        self.lbl_head_title = tk.Label(head_row, text=tr("app_title"),
                                       font=font(14, "bold"),
                                       bg=COLORS["header"],
                                       fg=COLORS["text"])
        self.lbl_head_title.pack(side='left')
        badge = tk.Label(head_row, text=TEST_SOLVER_VERSION,
                         font=font(8, mono=True), bg=COLORS["surface"],
                         fg=COLORS["subtext"], padx=7, pady=2)
        badge.pack(side='left', padx=(10, 0))

        self.lbl_subtitle = tk.Label(header, text=tr("main_subtitle"),
                                     font=font(8), bg=COLORS["header"],
                                     fg=COLORS["subtext"])
        self.lbl_subtitle.pack(anchor='w')

        # ---- Scrollable responsive body ----
        body_holder = tk.Frame(self, bg=COLORS["bg"])
        body_holder.pack(fill='both', expand=True,
                         padx=14, pady=(12, 6), side='top')
        self.scroll = ScrollFrame(body_holder, max_height=max_body_h)
        self.scroll.pack(fill='both', expand=True)
        self._build_status_card(self.scroll.inner)
        self._build_info_card(self.scroll.inner)
        self.banner_frame = None
        self._build_banner(self.scroll.inner)

        # ---- Footer ----
        footer = tk.Frame(self, bg=COLORS["bg"], padx=14, pady=12)
        footer.pack(fill='x', side='bottom')

        self.btn_exit = RoundedButton(footer, palette="ghost_danger",
                                      text=tr("btn_exit"),
                                      command=self.exit_app,
                                      font=font(9, "bold"), padx=16, pady=6)
        self.btn_exit.pack(side='right')
        self.btn_credits = RoundedButton(footer, palette="surface",
                                         text=tr("btn_credits"),
                                         command=self.open_credits,
                                         font=font(9, "bold"), padx=16, pady=6)
        self.btn_credits.pack(side='right', padx=(0, 8))
        self.btn_settings = RoundedButton(footer, palette="surface",
                                          text=tr("btn_settings"),
                                          command=self.open_settings,
                                          font=font(9, "bold"), padx=16, pady=6)
        self.btn_settings.pack(side='left')

        self.protocol("WM_DELETE_WINDOW", self.hide_to_background)

        subscribe_ui(self.on_service_snapshot)
        self.bind("<Destroy>", self._on_destroy, add="+")

        # Paint the REAL current state immediately
        self.on_service_snapshot(_controller.snapshot())
        self.after(60, self._finalize_geometry)

    # ------------------------------ layout ---------------------------------
    def _finalize_geometry(self):
        needed = self.scroll.content_height() + 4
        visible = min(needed, self.scroll.max_height)
        self.scroll.canvas.configure(height=visible)
        self.update_idletasks()
        center_on_screen(self, self.WIDTH, self.winfo_reqheight())
        self.minsize(self.WIDTH, self.winfo_reqheight())

    def _card(self, parent):
        card = tk.Frame(parent, bg=COLORS["panel"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        card.pack(fill='x', pady=(0, 12))
        return card

    def _build_status_card(self, parent):
        card = self._card(parent)
        inner = tk.Frame(card, bg=COLORS["panel"], padx=14, pady=12)
        inner.pack(fill='both', expand=True)

        top = tk.Frame(inner, bg=COLORS["panel"])
        top.pack(fill='x')
        self.dot = StatusDot(top, diameter=13, bg=COLORS["panel"])
        self.dot.pack(side='left')
        self.lbl_status = tk.Label(top, text="", font=font(13, "bold"),
                                   bg=COLORS["panel"], fg=COLORS["muted"])
        self.lbl_status.pack(side='left', padx=(9, 0))
        self.lbl_service_cap = tk.Label(top, text=tr("lbl_service_status"),
                                        font=font(8), bg=COLORS["panel"],
                                        fg=COLORS["muted"])
        self.lbl_service_cap.pack(side='right')

        # Sanitized error / crash detail line (kept in place; empty = invisible)
        self.lbl_detail = tk.Label(inner, text="", font=font(8),
                                   bg=COLORS["panel"], fg=COLORS["red"],
                                   justify='left', wraplength=400, anchor='w',
                                   pady=0)
        self.lbl_detail.pack(fill='x')

        meta = tk.Frame(inner, bg=COLORS["panel"])
        meta.pack(fill='x', pady=(8, 2))
        self.lbl_uptime_cap = tk.Label(meta, text=tr("uptime_label"),
                                       font=font(8), bg=COLORS["panel"],
                                       fg=COLORS["muted"])
        self.lbl_uptime_cap.pack(side='left')
        self.lbl_uptime = tk.Label(meta, text="-", font=font(8, mono=True),
                                   bg=COLORS["panel"], fg=COLORS["text"])
        self.lbl_uptime.pack(side='left', padx=(6, 14))

        self.lbl_check_cap = tk.Label(meta, text=tr("last_check_label"),
                                      font=font(8), bg=COLORS["panel"],
                                      fg=COLORS["muted"])
        self.lbl_check_cap.pack(side='left')
        self.lbl_lastcheck = tk.Label(meta, text="-", font=font(8, mono=True),
                                      bg=COLORS["panel"], fg=COLORS["text"])
        self.lbl_lastcheck.pack(side='left', padx=(6, 0))

        btns = tk.Frame(inner, bg=COLORS["panel"])
        btns.pack(fill='x', pady=(12, 2))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        self.btn_start = RoundedButton(btns, palette="green",
                                     text=tr("btn_start_service"),
                                     command=self.start_clicked,
                                     font=font(10, "bold"), pady=8)
        self.btn_start.grid(row=0, column=0, sticky='ew', padx=(0, 5))

        self.btn_stop = RoundedButton(btns, palette="red",
                                    text=tr("btn_stop_service"),
                                    command=self.stop_clicked,
                                    font=font(10, "bold"), pady=8)
        self.btn_stop.grid(row=0, column=1, sticky='ew', padx=(5, 0))

        self.lbl_monitor_hint = tk.Label(inner, text=tr("monitor_hint"),
                                         font=font(7, slant="italic"),
                                         bg=COLORS["panel"],
                                         fg=COLORS["muted"])
        self.lbl_monitor_hint.pack(anchor='e', pady=(4, 0))

    def _build_info_card(self, parent):
        card = self._card(parent)
        inner = tk.Frame(card, bg=COLORS["panel"], padx=14, pady=10)
        inner.pack(fill='both', expand=True)

        rows = tk.Frame(inner, bg=COLORS["panel"])
        rows.pack(fill='x')
        rows.columnconfigure(0, weight=1)

        self._info_refs = {}
        self._caption_refs = {}
        info_rows = [
            ("provider", tr("info_provider")),
            ("model", tr("info_model")),
            ("language", tr("info_language")),
        ]
        for i, (key, caption) in enumerate(info_rows):
            cap_lbl = tk.Label(rows, text=caption, font=font(7, "bold"),
                               bg=COLORS["panel"], fg=COLORS["muted"])
            cap_lbl.grid(row=i * 2, column=0, sticky='w',
                         pady=(6 if i else 2, 1))
            val_lbl = tk.Label(rows, text="-", font=font(9),
                               bg=COLORS["panel"], fg=COLORS["text"],
                               anchor='w', justify='left', wraplength=280)
            val_lbl.grid(row=i * 2 + 1, column=0, columnspan=2, sticky='we')
            self._caption_refs[key] = cap_lbl
            self._info_refs[key] = val_lbl

        hk_row = tk.Frame(inner, bg=COLORS["panel"])
        hk_row.pack(fill='x', pady=(8, 2))
        self._hk_caption_a = tk.Label(hk_row, text=tr("info_hotkey_analyze"),
                                      font=font(7, "bold"), bg=COLORS["panel"],
                                      fg=COLORS["muted"])
        self._hk_caption_a.pack(side='left')
        self.pill_capture = tk.Label(hk_row, text="", font=font(9, mono=True),
                                     bg=COLORS["surface"], fg=COLORS["accent"],
                                     padx=9, pady=2)
        self.pill_capture.pack(side='left', padx=(8, 18))
        self._hk_caption_c = tk.Label(hk_row, text=tr("info_hotkey_close"),
                                      font=font(7, "bold"), bg=COLORS["panel"],
                                      fg=COLORS["muted"])
        self._hk_caption_c.pack(side='left')
        self.pill_close = tk.Label(hk_row, text="", font=font(9, mono=True),
                                   bg=COLORS["surface"], fg=COLORS["orange"],
                                   padx=9, pady=2)
        self.pill_close.pack(side='left', padx=(8, 0))
        self.update_info()

    def _build_banner(self, parent):
        key = ""
        prov = config.get("providers", {}).get(config.get("current_provider", ""), {})
        key = (prov.get("api_key") or "").strip()
        if key:
            return
        self.banner_frame = tk.Frame(
            parent, bg="#33291c", highlightbackground=COLORS["yellow"],
            highlightthickness=1)
        self.banner_frame.pack(fill='x', pady=(0, 12))
        inner = tk.Frame(self.banner_frame, bg="#33291c", padx=12, pady=10)
        inner.pack(fill='both', expand=True)

        tk.Label(inner, text=tr("banner_no_key_title"), font=font(9, "bold"),
                 bg="#33291c", fg=COLORS["yellow"]).pack(anchor='w')
        tk.Label(inner, text=tr("banner_no_key_msg"), font=font(8),
                 bg="#33291c", fg="#d8cba8", justify='left',
                 wraplength=380).pack(anchor='w', pady=(2, 6))
        RoundedButton(inner, palette="accent", text=tr("banner_btn"),
                    command=self.open_settings, font=font(8, "bold"),
                    padx=12, pady=4).pack(anchor='w')
        self.refresh_banner()

    def refresh_banner(self):
        """Re-evaluate whether the missing-API-key banner should be visible."""
        prov = config.get("providers", {}).get(config.get("current_provider", ""), {})
        has_key = bool((prov.get("api_key") or "").strip())
        if has_key:
            if self.banner_frame is not None and self.banner_frame.winfo_exists():
                self.banner_frame.destroy()
                self.banner_frame = None
        elif self.banner_frame is None:
            self._build_banner(self.scroll.inner)
            self._finalize_geometry()

    # --------------------------- data refresh -------------------------------
    def update_info(self):
        prov_id = config.get("current_provider", "groq")
        prov_data = config.get("providers", {}).get(prov_id, {})
        model = prov_data.get("model", "") or "-"
        lang_name = tr("lang_es") if config.get("language", "es") == "es" else tr("lang_en")

        self._info_refs["provider"].config(text=prov_id.upper())
        self._info_refs["model"].config(text=model)
        self._info_refs["language"].config(text=lang_name)
        self.pill_capture.config(
            text=(config.get("hotkey_analyze", "") or "-").upper())
        self.pill_close.config(
            text=(config.get("hotkey_close", "") or "-").upper())

    def refresh_texts(self):
        """Re-apply localized texts without recreating the window."""
        self.title(f"{tr('app_title')} - {TEST_SOLVER_VERSION}")
        # Direct reconfiguration of known widgets
        self.lbl_head_title.config(text=tr("app_title"))
        self.lbl_subtitle.config(text=tr("main_subtitle"))
        self.btn_start.config(text=tr("btn_start_service"))
        self.btn_stop.config(text=tr("btn_stop_service"))
        self.btn_exit.config(text=tr("btn_exit"))
        self.btn_credits.config(text=tr("btn_credits"))
        self.btn_settings.config(text=tr("btn_settings"))
        self.lbl_service_cap.config(text=tr("lbl_service_status"))
        self.lbl_uptime_cap.config(text=tr("uptime_label"))
        self.lbl_check_cap.config(text=tr("last_check_label"))
        self.lbl_monitor_hint.config(text=tr("monitor_hint"))
        self._hk_caption_a.config(text=tr("info_hotkey_analyze"))
        self._hk_caption_c.config(text=tr("info_hotkey_close"))
        for key in ("provider", "model", "language"):
            caption = {"provider": tr("info_provider"),
                       "model": tr("info_model"),
                       "language": tr("info_language")}[key]
            self._caption_refs[key].config(text=caption)
        snap = _controller.snapshot()
        self.lbl_status.config(text=_status_display(snap["state"])[0])
        self.update_info()
        self.refresh_banner()

    # ------------------------- service interactions --------------------------
    def start_clicked(self):
        if not _controller.start():
            snap = _controller.snapshot()
            if snap["state"] != STATE_RUNNING:
                self.btn_start.flash_error()

    def stop_clicked(self):
        if not _controller.stop():
            snap = _controller.snapshot()
            if snap["state"] not in (STATE_STOPPED,):
                self.btn_stop.flash_error()

    def open_settings(self):
        open_settings_window(self.root)

    def open_credits(self):
        CreditsModal(self)

    def hide_to_background(self):
        """Closing the window keeps the app alive in the background."""
        self.withdraw()
        show_toast(self.root, tr("toast_title"), tr("toast_background"))

    def exit_app(self):
        if messagebox.askyesno(tr("msg_exit_title"), tr("msg_exit_confirm"),
                               parent=self):
            graceful_shutdown(self.root)

    # --------------------------- state observer -----------------------------
    def on_service_snapshot(self, snap):
        if not self.winfo_exists():
            return
        state = snap.get("state", STATE_STOPPED)
        text, color = _status_display(state)
        self.lbl_status.config(text=text, fg=color)
        self.dot.set_state(state)

        detail = snap.get("detail")
        if detail:
            self.lbl_detail.config(text=detail, pady=2)
        else:
            self.lbl_detail.config(text="", pady=0)

        self.lbl_uptime.config(text=fmt_uptime(snap.get("uptime")))
        self.lbl_lastcheck.config(text=fmt_clock(snap.get("last_check")))

        self.btn_start.set_enabled(state in (STATE_STOPPED, STATE_CRASHED))
        self.btn_stop.set_enabled(state == STATE_RUNNING)

        failed_op = snap.get("failed_op")
        if failed_op == "start":
            self._queue_flash(self.btn_start)
        elif failed_op == "stop":
            self._queue_flash(self.btn_stop)

    def _queue_flash(self, button):
        job = self.after(10, lambda b=button: b.flash_error())
        self._flash_jobs.append(job)

    def _on_destroy(self, event):
        if event.widget is self:
            unsubscribe_ui(self.on_service_snapshot)


# Graceful application shutdown used by Exit button and the F9 close-hotkey
def graceful_shutdown(root=None):
    try:
        if _controller is not None:
            if _controller.state in (STATE_RUNNING, STATE_STARTING,
                                     STATE_STOPPING) or _controller.probe_real():
                _controller.stop(wait=True)
    except Exception as e:
        print(f"Shutdown warning: {sanitize_error(str(e))}")
    if root is not None:
        try:
            root.destroy()
        except Exception:
            pass


# Settings Configuration Window

def setup_ttk_style():
    """Dark theme for ttk comboboxes matching the Catppuccin palette."""
    style = ttk.Style()
    try:
        style.theme_use('default')
    except Exception:
        pass
    style.configure("TCombobox",
                    fieldbackground=COLORS["panel"],
                    background=COLORS["surface"],
                    foreground=COLORS["text"],
                    arrowcolor=COLORS["accent"],
                    bordercolor=COLORS["border"],
                    lightcolor=COLORS["panel"],
                    darkcolor=COLORS["panel"])
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["panel"])],
              foreground=[("readonly", COLORS["text"])])
    try:
        style.option_add("*TCombobox*Listbox*Background", COLORS["panel"])
        style.option_add("*TCombobox*Listbox*Foreground", COLORS["text"])
        style.option_add("*TCombobox*Listbox*selectBackground",
                         COLORS["surface_hi"])
        style.option_add("*TCombobox*Listbox*selectForeground",
                         COLORS["text"])
        style.option_add("*TCombobox*Listbox*Font",
                         "{%s} 9" % FONT_FAMILY)
    except Exception:
        pass


class SettingsWindow(tk.Toplevel):
    WIDTH = 470

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title(tr("settings_title"))
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        apply_icon(self)
        setup_ttk_style()

        screen_h = self.winfo_screenheight()
        max_body_h = max(screen_h - 210, 260)

        # ---- State vars (needed by section builders) ----
        self.show_key = tk.BooleanVar(value=False)
        self.current_prov = tk.StringVar(
            value=config.get("current_provider", "groq"))
        # Display variable for the provider combobox (friendly label); the
        # ID source of truth stays in current_prov.
        self.prov_display = tk.StringVar()
        self.lang_var = tk.StringVar(
            value=tr("lang_es") if config.get("language", "es") == "es" else tr("lang_en"))

        # ---- Scrollable responsive body ----
        body_holder = tk.Frame(self, bg=COLORS["bg"])
        body_holder.pack(fill='both', expand=True,
                         padx=16, pady=(14, 6))
        self.scroll = ScrollFrame(body_holder, max_height=max_body_h)
        self.scroll.pack(fill='both', expand=True)

        self._build_provider_section(self.scroll.inner)
        self._build_prefs_section(self.scroll.inner)
        self._build_service_section(self.scroll.inner)

        # ---- Fixed footer: test status + actions ----
        footer = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=12)
        footer.pack(fill='x', side='bottom')

        self.lbl_status_conn = tk.Label(footer, text="", font=font(8),
                                        bg=COLORS["bg"], fg=COLORS["subtext"],
                                        justify='left', wraplength=180,
                                        anchor='w')
        self.lbl_status_conn.pack(side='left', fill='x', expand=True)

        RoundedButton(footer, palette="red", text=tr("btn_cancel"),
                    command=self.cerrar, font=font(9, "bold"),
                    padx=14, pady=6).pack(side='right', padx=(8, 0))
        RoundedButton(footer, palette="green", text=tr("btn_save"),
                    command=self.save_settings, font=font(9, "bold"),
                    padx=16, pady=6).pack(side='right')
        RoundedButton(footer, palette="surface", text=tr("btn_test"),
                    command=self.test_connection, font=font(9, "bold"),
                    padx=12, pady=6).pack(side='right', padx=(0, 8))

        self.load_provider_data()

        subscribe_ui(self.on_service_snapshot)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.on_service_snapshot(_controller.snapshot())

        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.after(60, self._finalize_geometry)

    # ------------------------------ layout ---------------------------------
    def _finalize_geometry(self):
        needed = self.scroll.content_height() + 4
        visible = min(needed, self.scroll.max_height)
        self.scroll.canvas.configure(height=visible)
        self.update_idletasks()
        center_on_screen(self, self.WIDTH, self.winfo_reqheight())

    def _section_title(self, parent, text):
        tk.Label(parent, text=text, font=font(8, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(anchor='w',
                                                            pady=(0, 6))

    def _field_label(self, parent, text):
        tk.Label(parent, text=text, font=font(9),
                 bg=COLORS["bg"], fg=COLORS["subtext"]).pack(anchor='w')

    def _entry(self, parent, **kw):
        return tk.Entry(parent, bg=COLORS["panel"], fg=COLORS["text"],
                        insertbackground=COLORS["text"], relief='flat',
                        font=font(10),
                        highlightthickness=1,
                        highlightbackground=COLORS["border"],
                        highlightcolor=COLORS["accent"], **kw)

    def _card(self, parent):
        card = tk.Frame(parent, bg=COLORS["panel"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        card.pack(fill='x', pady=(0, 14))
        return card

    def _build_provider_section(self, parent):
        self._section_title(parent, tr("api_config_title"))
        card = self._card(parent)
        inner = tk.Frame(card, bg=COLORS["panel"], padx=14, pady=12)
        inner.pack(fill='both', expand=True)

        # Provider selector: friendly display labels resolved to ids.
        self._field_label(inner, tr("lbl_provider"))
        self._prov_ids = [pid for pid in PROVIDER_ORDER if pid in PROVIDERS]
        self._prov_labels = [f"{PROVIDERS[pid].ui_label()}  ·  "
                             f"{provider_badges(pid)}"
                             for pid in self._prov_ids]
        self.cb_provider = ttk.Combobox(
            inner, values=self._prov_labels,
            textvariable=self.prov_display,
            font=font(10), state="readonly")
        idx = (self._prov_ids.index(self.current_prov.get())
               if self.current_prov.get() in self._prov_ids else 0)
        if self._prov_labels:
            self.prov_display.set(self._prov_labels[idx])
        self.cb_provider.pack(fill='x', pady=(3, 4))
        self.cb_provider.bind("<<ComboboxSelected>>",
                              lambda e: self.on_provider_change())

        self.lbl_prov_info = tk.Label(inner, text="", font=font(8),
                                      bg=COLORS["panel"],
                                      fg=COLORS["muted"],
                                      justify='left', anchor='w',
                                      wraplength=380)
        self.lbl_prov_info.pack(fill='x', pady=(0, 8))

        self._field_label(inner, tr("lbl_api_key"))
        key_frame = tk.Frame(inner, bg=COLORS["panel"])
        key_frame.pack(fill='x', pady=(3, 10))

        self.ent_key = self._entry(key_frame, show="*")
        self.ent_key.pack(side='left', fill='x', expand=True, ipady=5)

        chk_show = tk.Checkbutton(
            key_frame,
            text=tr("lbl_show_key"),
            variable=self.show_key,
            command=self.toggle_key_visibility,
            bg=COLORS["panel"], fg=COLORS["subtext"],
            activebackground=COLORS["panel"], activeforeground=COLORS["text"],
            selectcolor=COLORS["panel"], font=font(8), cursor="hand2",
            relief='flat', highlightthickness=0, bd=0)
        chk_show.pack(side='right', padx=(8, 2))

        self.lbl_url = tk.Label(inner, text=tr("lbl_base_url"), font=font(9),
                                bg=COLORS["panel"], fg=COLORS["subtext"])
        self.lbl_url.pack(anchor='w')
        self.ent_url = self._entry(inner)
        self.ent_url.pack(fill='x', pady=(3, 10), ipady=5)

        self._field_label(inner, tr("lbl_model"))
        self.cb_model = ttk.Combobox(inner, font=font(10))
        self.cb_model.pack(fill='x', pady=(3, 2))

    def _build_prefs_section(self, parent):
        self._section_title(parent, tr("section_prefs"))
        card = self._card(parent)
        inner = tk.Frame(card, bg=COLORS["panel"], padx=14, pady=12)
        inner.pack(fill='both', expand=True)
        inner.columnconfigure(1, weight=1)

        tk.Label(inner, text=tr("lbl_language"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"]).grid(
            row=0, column=0, sticky='w', pady=4)
        self.cb_lang = ttk.Combobox(inner, values=[tr("lang_es"), tr("lang_en")],
                                    textvariable=self.lang_var, font=font(10),
                                    state="readonly")
        self.cb_lang.grid(row=0, column=1, sticky='we', padx=(12, 0), pady=4)

        tk.Label(inner, text=tr("lbl_hotkey_analyze"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"]).grid(
            row=1, column=0, sticky='w', pady=4)
        self.ent_hk_analyze = tk.Entry(
            inner, bg=COLORS["header"], fg=COLORS["accent"],
            insertbackground=COLORS["text"], relief='flat',
            font=font(10, mono=True), width=10,
            justify='center',
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"])
        self.ent_hk_analyze.grid(row=1, column=1, sticky='w',
                                 padx=(12, 0), pady=4, ipady=4)
        self.ent_hk_analyze.insert(
            0, str(config.get("hotkey_analyze", "f8") or "f8"))

        tk.Label(inner, text=tr("lbl_hotkey_close"), font=font(9),
                 bg=COLORS["panel"], fg=COLORS["subtext"]).grid(
            row=2, column=0, sticky='w', pady=4)
        self.ent_hk_close = tk.Entry(
            inner, bg=COLORS["header"], fg=COLORS["orange"],
            insertbackground=COLORS["text"], relief='flat',
            font=font(10, mono=True), width=10,
            justify='center',
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"])
        self.ent_hk_close.grid(row=2, column=1, sticky='w',
                               padx=(12, 0), pady=4, ipady=4)
        self.ent_hk_close.insert(
            0, str(config.get("hotkey_close", "f9") or "f9"))

    def _build_service_section(self, parent):
        self._section_title(parent, tr("section_service"))
        card = self._card(parent)
        inner = tk.Frame(card, bg=COLORS["panel"], padx=14, pady=12)
        inner.pack(fill='both', expand=True)

        top = tk.Frame(inner, bg=COLORS["panel"])
        top.pack(fill='x')
        self.dot = StatusDot(top, diameter=11, bg=COLORS["panel"])
        self.dot.pack(side='left')
        self.lbl_status_val = tk.Label(top, text="", font=font(11, "bold"),
                                       bg=COLORS["panel"])
        self.lbl_status_val.pack(side='left', padx=(8, 0))

        btns = tk.Frame(top, bg=COLORS["panel"])
        btns.pack(side='right')
        self.btn_start_service = RoundedButton(
            btns, palette="green", text=tr("btn_start_service"),
            command=self.start_service_click, font=font(8, "bold"),
            padx=10, pady=5)
        self.btn_start_service.pack(side='left', padx=(0, 6))
        self.btn_stop_service = RoundedButton(
            btns, palette="red", text=tr("btn_stop_service"),
            command=self.stop_service_click, font=font(8, "bold"),
            padx=10, pady=5)
        self.btn_stop_service.pack(side='left')

        self.lbl_svc_detail = tk.Label(inner, text="", font=font(8),
                                       bg=COLORS["panel"], fg=COLORS["red"],
                                       justify='left', wraplength=380,
                                       anchor='w', pady=0)
        self.lbl_svc_detail.pack(fill='x')

    # ------------------------------ behavior --------------------------------
    def toggle_key_visibility(self):
        self.ent_key.config(show="" if self.show_key.get() else "*")

    def open_credits(self):
        CreditsModal(self)

    def on_provider_change(self):
        self._sync_provider_selection()
        self.load_provider_data()

    def _sync_provider_selection(self):
        """Resolve the combobox display label back to the provider ID."""
        label = self.prov_display.get()
        try:
            idx = self._prov_labels.index(label)
            self.current_prov.set(self._prov_ids[idx])
        except (ValueError, AttributeError):
            pass

    def load_provider_data(self):
        prov = self.current_prov.get()
        prov_data = config.get("providers", {}).get(prov, {})

        self.lbl_prov_info.config(
            text=f"{provider_badges(prov)}\n{provider_note(prov)}".strip(" \n"))

        self.ent_key.delete(0, tk.END)
        self.ent_key.insert(0, prov_data.get("api_key", ""))

        meta = PROVIDERS.get(prov)
        default_url = getattr(meta, "default_base", "") if meta else ""
        stored_url = prov_data.get("base_url", "")
        self.ent_url.config(state='normal')
        self.ent_url.delete(0, tk.END)
        # Always editable: users may override endpoints; prefilled with the
        # provider's official API URL when nothing custom was saved.
        self.ent_url.insert(0, stored_url or default_url)

        models = list(PROVIDER_MODELS.get(prov, []))

        selected_model = prov_data.get("model", "")
        if models:
            if selected_model and selected_model not in models:
                models.append(selected_model)
            selected_model = selected_model or models[0]
        self.cb_model.config(values=models)
        self.cb_model.set(selected_model or "")

    def start_service_click(self):
        initiated = _controller.start()
        if not initiated:
            snap = _controller.snapshot()
            if snap["state"] != STATE_RUNNING:
                self.btn_start_service.flash_error()

    def stop_service_click(self):
        initiated = _controller.stop()
        if not initiated:
            snap = _controller.snapshot()
            if snap["state"] not in (STATE_STOPPED,):
                self.btn_stop_service.flash_error()

    def on_service_snapshot(self, snap):
        if not self.winfo_exists():
            return
        state = snap.get("state", STATE_STOPPED)
        text, color = _status_display(state)
        self.lbl_status_val.config(text=text, fg=color)
        self.dot.set_state(state)

        detail = snap.get("detail")
        self.lbl_svc_detail.config(text=detail or "", pady=2 if detail else 0)

        self.btn_start_service.set_enabled(
            state in (STATE_STOPPED, STATE_CRASHED))
        self.btn_stop_service.set_enabled(state == STATE_RUNNING)

        failed_op = snap.get("failed_op")
        if failed_op == "start":
            self.after(10, lambda b=self.btn_start_service: b.flash_error())
        elif failed_op == "stop":
            self.after(10, lambda b=self.btn_stop_service: b.flash_error())

    def test_connection(self):
        self._sync_provider_selection()
        key = self.ent_key.get().strip()
        prov = self.current_prov.get()
        base_url = self.ent_url.get().strip()
        model = self.cb_model.get().strip()

        if not key:
            self.lbl_status_conn.config(
                text=f"Error: {tr('err_invalid_key')}", fg=COLORS["red"])
            return

        self.lbl_status_conn.config(text=tr("calling_api"), fg=COLORS["accent"])

        def run_test():
            ok = False
            msg = ""
            try:
                provider_obj = PROVIDERS.get(prov, CustomProvider())
                url = provider_obj.endpoint(base_url, model)
                headers = provider_obj.get_headers(key)
                payload = provider_obj.ping_payload(model)
                r = requests.post(url, headers=headers, json=payload,
                                  timeout=10)
                if r.status_code == 200:
                    ok = True
                    msg = tr("success_conn")
                else:
                    try:
                        err_text = r.json().get('error', {}).get(
                            'message', f"HTTP {r.status_code}")
                    except Exception:
                        err_text = f"HTTP {r.status_code}"
                    msg = f"Error: {sanitize_error(err_text)}"
            except Exception as e:
                msg = f"Error: {sanitize_error(str(e))}"
            color = COLORS["green"] if ok else COLORS["red"]

            def apply():
                try:
                    self.lbl_status_conn.config(text=msg, fg=color)
                except Exception:
                    pass
            try:
                self.after(0, apply)
            except Exception:
                pass

        threading.Thread(target=run_test, daemon=True).start()

    def save_settings(self):
        global config

        self._sync_provider_selection()
        prov = self.current_prov.get()
        key = self.ent_key.get().strip()
        base_url = self.ent_url.get().strip()
        model = self.cb_model.get().strip()

        lang_sel = self.lang_var.get()
        new_lang = "es" if lang_sel == tr("lang_es") else "en"

        new_hk_analyze = self.ent_hk_analyze.get().strip().lower()
        new_hk_close = self.ent_hk_close.get().strip().lower()

        if not new_hk_analyze or not new_hk_close:
            messagebox.showwarning("Test Solver AI", tr("msg_hotkey_invalid"),
                                   parent=self)
            return
        if new_hk_analyze == new_hk_close:
            messagebox.showwarning("Test Solver AI", tr("msg_hotkey_invalid"),
                                   parent=self)
            return
        try:
            keyboard.parse_hotkey(new_hk_analyze)
            keyboard.parse_hotkey(new_hk_close)
        except Exception:
            messagebox.showwarning("Test Solver AI", tr("msg_hotkey_invalid"),
                                   parent=self)
            return

        lang_changed = (new_lang != config.get("language", "es"))

        config["current_provider"] = prov
        config["language"] = new_lang
        config["hotkey_analyze"] = new_hk_analyze
        config["hotkey_close"] = new_hk_close

        if prov not in config["providers"]:
            config["providers"][prov] = {}
        config["providers"][prov]["api_key"] = key
        config["providers"][prov]["base_url"] = base_url
        config["providers"][prov]["model"] = model

        save_config(config)

        # Live-reload hooks only when the service is REALLY running
        was_running = (_controller.state == STATE_RUNNING
                       or _controller.probe_real())
        if was_running:
            _controller.reload_hotkeys()

        # Keep every visible surface synchronized
        if _main_window is not None and _main_window.winfo_exists():
            if lang_changed:
                _main_window.refresh_texts()
            else:
                _main_window.update_info()
                _main_window.refresh_banner()

        messagebox.showinfo("Test Solver AI", tr("msg_saved"), parent=self)
        self.cerrar()

    def cerrar(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_destroy(self, event):
        if event.widget is self:
            unsubscribe_ui(self.on_service_snapshot)


def open_settings_window(root):
    global _settings_window
    if _settings_window is not None and _settings_window.winfo_exists():
        _settings_window.deiconify()
        _settings_window.lift()
        _settings_window.focus_force()
        return _settings_window
    _settings_window = SettingsWindow(root)
    return _settings_window

# Overlay window
class SolverOverlay(tk.Toplevel):
    def __init__(self, root, initial_state="loading", initial_data=None):
        super().__init__(root)
        self.root = root
        self.state_mode = initial_state

        self.setup_window()
        self.create_widgets()

        if initial_state == "loading":
            self.show_loading_view()
        elif initial_state == "result":
            self.show_result_view(initial_data)
        elif initial_state == "error":
            self.show_error_view(initial_data)

        fade_in(self, target=0.97)

    def setup_window(self):
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.0)
        apply_icon(self)

        screen_w = self.winfo_screenwidth()
        width = 340
        height = 430
        x = screen_w - width - 30
        y = 30
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        self.container = tk.Frame(
            self,
            bg=COLORS["bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self.container.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self.header = tk.Frame(self.container, bg=COLORS["header"],
                               height=34, cursor='fleur')
        self.header.pack(fill='x')
        self.header.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.header,
            text=tr("overlay_title"),
            font=font(10, "bold"),
            bg=COLORS["header"],
            fg=COLORS["accent"]
        )
        self.title_lbl.pack(side='left', padx=10, pady=4)

        self.close_btn = RoundedButton(
            self.header, palette="red", text='X',
            command=self.cerrar, font=font(8, "bold"),
            padx=9, pady=2
        )
        self.close_btn.pack(side='right', padx=6, pady=4)

        self.settings_btn = RoundedButton(
            self.header, palette="surface", text='Config',
            command=self.open_settings, font=font(8, "bold"),
            padx=7, pady=2
        )
        self.settings_btn.pack(side='right', padx=2, pady=4)

        self.copy_btn = RoundedButton(
            self.header, palette="surface", text=tr("btn_copy"),
            command=self.copy_to_clipboard, font=font(8, "bold"),
            padx=7, pady=2
        )

        self.content_frame = tk.Frame(self.container, bg=COLORS["bg"])
        self.content_frame.pack(fill='both', expand=True, padx=8, pady=8)

        self.header.bind('<Button-1>', self.start_drag)
        self.header.bind('<B1-Motion>', self.do_drag)

        self.bind('<Escape>', lambda e: self.cerrar())

        # Resize grip (monospace exception: decorative technical glyph)
        self.grip = tk.Label(
            self.container,
            text='//',
            bg=COLORS["header"],
            fg=COLORS["subtext"],
            cursor='size_nw_se',
            font=font(7, mono=True)
        )
        self.grip.pack(side='bottom', anchor='e', padx=4, pady=1)
        self.grip.bind('<Button-1>', self.start_resize)
        self.grip.bind('<B1-Motion>', self.do_resize)

    def open_settings(self):
        open_settings_window(self.root)

    def show_loading_view(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.state_mode = "loading"
        self.copy_btn.pack_forget()

        center_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        center_frame.place(relx=0.5, rely=0.5, anchor='center')

        loading_label = tk.Label(
            center_frame,
            text='⏳',
            font=(FONT_FAMILY, 22),
            bg=COLORS["bg"],
            fg=COLORS["accent"]
        )
        loading_label.pack(pady=5)

        text_label = tk.Label(
            center_frame,
            text=tr("analyzing"),
            font=font(11, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["text"]
        )
        text_label.pack(pady=2)

        subtext_label = tk.Label(
            center_frame,
            text=tr("calling_api"),
            font=font(9),
            bg=COLORS["bg"],
            fg=COLORS["subtext"]
        )
        subtext_label.pack()

        self.loading_dots = 0

        def animate():
            if self.winfo_exists() and self.state_mode == "loading":
                self.loading_dots = (self.loading_dots + 1) % 4
                dots = "." * self.loading_dots
                text_label.config(text=f"{tr('analyzing')}{dots}")
                self.after(500, animate)
        animate()

    def show_result_view(self, text_content):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.state_mode = "result"
        self.result_text = text_content

        self.copy_btn.pack(side='right', padx=2, pady=4)

        scrollbar = tk.Scrollbar(
            self.content_frame,
            bg=COLORS["surface"],
            troughcolor=COLORS["bg"],
            width=10
        )
        scrollbar.pack(side='right', fill='y')

        text_box = tk.Text(
            self.content_frame,
            wrap='word',
            font=font(10),
            bg=COLORS["bg"],
            fg=COLORS["text"],
            relief='flat',
            padx=6,
            pady=4,
            yscrollcommand=scrollbar.set,
            cursor='arrow',
            insertwidth=0,
            selectbackground=COLORS["surface"],
            selectforeground=COLORS["text"]
        )
        text_box.pack(fill='both', expand=True)
        scrollbar.config(command=text_box.yview)

        self.render_formatted_text(text_box, text_content)
        text_box.config(state='disabled')

    def render_formatted_text(self, text_box, text):
        text_box.tag_config("bold", font=font(10, "bold"),
                            foreground=COLORS["accent"])
        text_box.tag_config("header", font=font(12, "bold"),
                            foreground=COLORS["green"])
        text_box.tag_config("normal", font=font(10), foreground=COLORS["text"])

        lines = text.split('\n')
        for line in lines:
            if line.startswith('### ') or line.startswith('## '):
                clean_line = line.replace('### ', '').replace('## ', '') + '\n'
                text_box.insert(tk.END, clean_line, "header")
            elif '**' in line:
                parts = line.split('**')
                for idx, part in enumerate(parts):
                    tag = "bold" if idx % 2 != 0 else "normal"
                    text_box.insert(tk.END, part, tag)
                text_box.insert(tk.END, '\n', "normal")
            else:
                text_box.insert(tk.END, line + '\n', "normal")

    def show_error_view(self, error_msg):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.state_mode = "error"
        self.copy_btn.pack_forget()

        scrollbar = tk.Scrollbar(
            self.content_frame,
            bg=COLORS["surface"],
            troughcolor=COLORS["bg"],
            width=10
        )
        scrollbar.pack(side='right', fill='y')

        text_box = tk.Text(
            self.content_frame,
            wrap='word',
            font=font(10),
            bg=COLORS["bg"],
            fg=COLORS["red"],
            relief='flat',
            padx=8,
            pady=8,
            yscrollcommand=scrollbar.set
        )
        text_box.pack(fill='both', expand=True)
        scrollbar.config(command=text_box.yview)

        text_box.insert(tk.END, f"{tr('error_title')}\n\n", "bold")
        text_box.insert(tk.END, error_msg + "\n\n")

        text_box.insert(tk.END, tr("suggestion"), "bold")
        text_box.insert(tk.END, tr("suggestion_msg") + "\n\n")

        btn_retry = RoundedButton(
            self.content_frame,
            palette="accent",
            text=tr("btn_retry"),
            command=self.retry_analysis,
            font=font(9, "bold"),
            pady=5
        )
        btn_retry.pack(pady=4)

        text_box.config(state='disabled')

    def retry_analysis(self):
        self.show_loading_view()
        start_vision_analysis()

    def copy_to_clipboard(self):
        if hasattr(self, 'result_text') and self.result_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.result_text)
            self.root.update()
            self.copy_btn.config(text=tr("btn_copied"), bg=COLORS["green"],
                                 fg=COLORS["header"])
            self.after(2000, lambda: self.copy_btn.config(
                text=tr("btn_copy"), bg=self.copy_btn.p["bg"],
                fg=self.copy_btn.p.get("fg", COLORS["text"])))

    def cerrar(self):
        global _overlay
        _overlay = None
        fade_out(self, self.destroy)

    # Drag and Drop
    def start_drag(self, e):
        self._dx = e.x
        self._dy = e.y

    def do_drag(self, e):
        x = self.winfo_x() + e.x - self._dx
        y = self.winfo_y() + e.y - self._dy
        self.geometry(f"+{x}+{y}")

    # Resize
    def start_resize(self, e):
        self._rx = e.x_root
        self._ry = e.y_root
        self._rw = self.winfo_width()
        self._rh = self.winfo_height()

    def do_resize(self, e):
        nw = max(260, self._rw + e.x_root - self._rx)
        nh = max(180, self._rh + e.y_root - self._ry)
        self.geometry(f"{nw}x{nh}")


# Perform screenshot analysis dispatcher
def analyze_screenshot_flow(prov, key, base_url, model, lang):
    global _is_analyzing
    if _is_analyzing:
        return
    _is_analyzing = True

    time.sleep(0.25)

    try:
        if not key:
            raise ValueError(tr("err_invalid_key") + " Check config.")

        screenshot = ImageGrab.grab()
        image_b64 = optimize_image_to_base64(
            screenshot,
            quality=config.get("screenshot_quality", 85),
            max_width=config.get("max_width", 1600)
        )

        provider_obj = PROVIDERS.get(prov, CustomProvider())
        url = provider_obj.endpoint(base_url, model)
        headers = provider_obj.get_headers(key)
        payload = provider_obj.get_payload(model, image_b64, lang)

        response = requests.post(url, headers=headers, json=payload, timeout=25)

        if response.status_code != 200:
            try:
                err_data = response.json()
                err_msg = err_data.get('error', {}).get('message', 'Unknown Error')
            except Exception:
                err_msg = f"HTTP {response.status_code}"
            raise Exception(f"HTTP {response.status_code}: {err_msg}")

        answer = provider_obj.parse_response(response.json())
        _queue.put(('result', answer))

    except requests.exceptions.Timeout:
        _queue.put(('error', tr("err_timeout") + " " + tr("err_connection")))
    except requests.exceptions.ConnectionError:
        _queue.put(('error', tr("err_connection")))
    except Exception as e:
        # Sanitize any keys inside the traceback error message
        err_clean = sanitize_error(str(e))
        _queue.put(('error', err_clean))

    _is_analyzing = False


def start_vision_analysis():
    prov = config.get("current_provider", "groq")
    prov_data = config.get("providers", {}).get(prov, {})
    key = prov_data.get("api_key", "")
    base_url = prov_data.get("base_url", "")
    model = prov_data.get("model", "")
    lang = config.get("language", "es")

    threading.Thread(
        target=analyze_screenshot_flow,
        args=(prov, key, base_url, model, lang),
        daemon=True
    ).start()


# Periodic check of background queue (single Tk-thread entry point)
def process_queue(root):
    global _overlay, _last_snapshot
    try:
        while True:
            msg, data = _queue.get_nowait()
            if msg == 'init_loading':
                if _overlay is not None and _overlay.winfo_exists():
                    _overlay.destroy()
                _overlay = SolverOverlay(root, initial_state="loading")
            elif msg == 'result':
                if _overlay is not None and _overlay.winfo_exists():
                    _overlay.show_result_view(data)
                else:
                    _overlay = SolverOverlay(root, initial_state="result",
                                             initial_data=data)
            elif msg == 'error':
                if _overlay is not None and _overlay.winfo_exists():
                    _overlay.show_error_view(data)
                else:
                    _overlay = SolverOverlay(root, initial_state="error",
                                             initial_data=data)
            elif msg == 'show_settings':
                open_settings_window(root)
            elif msg == 'show_main':
                open_main_window(root)
            elif msg in ('service_state', 'service_tick'):
                _last_snapshot = data
                for fn in list(_ui_listeners):
                    try:
                        fn(data)
                    except Exception:
                        pass
            elif msg == 'toast':
                title, text = data
                show_toast(root, title, text)
            elif msg == 'request_quit':
                graceful_shutdown(root)
                return
            elif msg == 'quit':
                graceful_shutdown(root)
                return
    except queue.Empty:
        pass

    root.after(40, lambda: process_queue(root))


# Backwards-compatible thin wrappers around the controller
def start_service(root=None):
    return _controller.start()


def stop_service():
    return _controller.stop(wait=True)


def main():
    global config, _controller

    enable_dpi_awareness()
    register_open_sans_fonts()

    config = load_config()

    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.attributes('-alpha', 0)
    root.wm_attributes('-toolwindow', True)
    apply_icon(root)

    # Ensure single instance lock
    if not check_single_instance(root):
        print("Another instance is running. Opening its main panel...")
        root.destroy()
        return

    setup_ttk_style()

    # Service controller (single source of truth) - NOT started here.
    _controller = ServiceController()
    _controller.refresh_initial()   # probe REAL state; app opens Stopped.

    # Open the visible main control panel. This does NOT auto-start the service.
    open_main_window(root)

    root.after(40, lambda: process_queue(root))

    print("============================================")
    print(f"      TEST SOLVER AI - {TEST_SOLVER_VERSION.upper()}          ")
    print("============================================")
    print(f"   Provider: {config['current_provider'].upper()}")
    print("--------------------------------------------")
    hk_a = str(config.get('hotkey_analyze', 'f8')).upper()
    hk_c = str(config.get('hotkey_close', 'f9')).upper()
    print(f"   {hk_a} -> Analyze screen and view answers")
    print(f"   {hk_c} -> Close the application")
    print("   Service starts OFF; use Start Service in the panel.")
    print("============================================")

    # Preloaded key check - prompt settings on first launch without a key.
    prov = config.get("current_provider", "groq")
    prov_data = config.get("providers", {}).get(prov, {})
    current_key = prov_data.get("api_key", "")

    if not current_key:
        root.after(250, lambda: open_settings_window(root))
    else:
        def hint_toast():
            show_toast(
                root,
                tr("toast_title"),
                tr("toast_msg").format(hotkey=hk_a)
            )
        root.after(900, hint_toast)

    try:
        root.mainloop()
    finally:
        # Guarantee zero residual processes even if a daemon thread lingers.
        try:
            if _controller is not None and (_controller.state == STATE_RUNNING
                                            or _controller.probe_real()):
                _controller.stop(wait=True)
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    main()
