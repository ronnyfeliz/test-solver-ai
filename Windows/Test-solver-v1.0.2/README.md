# 🎯 Test Solver AI - v1.0.2

Herramienta de escritorio para Windows que analiza preguntas de opción múltiple
en tu pantalla usando IA de visión y muestra la respuesta al instante en un
overlay flotante.

> **F8** → captura y analiza la pantalla · **F9** → cierra la aplicación

---

## ✨ Características

- **Análisis con un solo hotkey**: captura optimizada de pantalla → LLM de visión → respuesta explicada.
- **Overlay flotante** siempre visible con vistas de carga / resultado / error, copiar respuesta y reintentar.
- **Panel principal** con estado real del servicio, tiempo activo, última verificación e info del proveedor/modelo.
- **Máquina de estados real**: el servicio arranca apagado a propósito; estados `detenido / iniciando / ejecución / deteniendo / caído` sondeados desde el hook real del sistema, con watchdog que detecta caídas y permite recuperar el servicio.
- **Multi-proveedor extensible** con niveles gratuitos reales.
- **Bilingüe ES/EN completo**, aplicado en vivo sin reiniciar.
- Tipografía **Open Sans** incrustada (no requiere instalación) y botones redondeados modernos con estados hover/presionado/deshabilitado/error.
- Notificaciones toast, instancia única, configuración persistente junto al ejecutable.

## 🔌 Proveedores soportados

| Proveedor | Costo | Visión (pantallazos) | Nota |
|---|---|---|---|
| **Groq** (`qwen/qwen3.6-27b`) | Gratis* | ✅ | Cuota por minuto/día según modelo |
| **Google Gemini (AI Studio)** | Gratis* | ✅ | Nivel gratuito sin tarjeta; Flash ≈10 rpm/250 día |
| **OpenRouter** (modelos `:free`) | Gratis* | ✅ según modelo | Gemma 4, Nemotron Nano VL, etc.; ~50 req/día |
| **OpenCode Zen (Big Pickle)** | Gratis (temporal) | ❌ solo texto/código | Requiere clave de OpenCode Zen |
| **DeepSeek oficial** | Pago (económico) | ❌ | `deepseek-chat` / `deepseek-reasoner` |
| **OpenAI** | Pago | ✅ gpt-4o-mini | Requiere crédito prepagado |
| **Personalizado** | Depende | Depende | Cualquier endpoint compatible con OpenAI |

\* Sujeto a las cuotas vigentes de cada servicio.

La app detecta modelos retirados (p. ej. los antiguos `meta-llama/*` de Groq,
hoy HTTP 404) y **repara automáticamente** la configuración al arrancar.

## 🚀 Uso rápido (ejecutable)

1. Descarga `test_solver_v1.0.2.exe` (ver [Releases](../../releases)).
2. Ejecútalo: si falta la clave del proveedor actual, se abrirá **Ajustes** automáticamente.
3. Pega tu clave API (se guarda **solo localmente**, junto al exe).
4. Pulsa **Iniciar servicio** y usa **F8** sobre cualquier pregunta.

> El cierre de la ventana lo deja minimizado al fondo; usa **Salir** o F9 para terminar de verdad.

## 🛠️ Ejecutar desde código fuente

```bash
cd code_source_v1.0.2
pip install requests pillow keyboard pyinstaller
python test_solver_v1.0.2.py
```

Requisitos: Windows 10/11, Python 3.10+, pantalla ≥ 1280x720 recomendada.

## 📦 Construir el ejecutable

```bash
cd code_source_v1.0.2
python -m PyInstaller test_solver_v1.0.2.spec --noconfirm --clean
# resultado en dist/test_solver_v1.0.2.exe
```

## ⚙️ Configuración

- El archivo `config.json` se crea **junto al ejecutable/script** (nunca en rutas relativas al sistema). Plantilla limpia: [`config.example.json`](code_source_v1.0.2/config.example.json).
- Desde **Ajustes** puedes cambiar proveedor, clave, endpoint, modelo, idioma y hotkeys; todo se aplica en caliente si el servicio está corriendo.
- Las claves **jamás se envían a los logs**: cualquier error se sanitiza antes de mostrarse.

## 🔒 Seguridad y privacidad

- Ninguna credencial está hardcodeada en el código fuente.
- Este repositorio excluye mediante `.gitignore`: `config.json`, logs, binarios de compilación, respaldos internos y notas personales.
- Si alguna vez filtraste una clave (p. ej. en un respaldo antiguo), **revócala** en el panel de tu proveedor antes de publicar.

## 🗂️ Estructura

```
├── code_source_v1.0.2/     # Código fuente + spec de PyInstaller
│   ├── media/fonts/        # Open Sans (SIL OFL)
│   ├── config.example.json # Plantilla limpia de configuración
│   └── test_solver_v1.0.2.py
├── media/                  # Iconos del proyecto
└── README.md
```

## 👥 Créditos

| Rol | Persona |
|---|---|
| **Autor original y creador de la aplicación** | **Alex Hatton** |
| **Colaborador GUI** (interfaz gráfica moderna, arquitectura y empaquetado) | **Ronny Feliz** · [github.com/ronnyfeliz](https://github.com/ronnyfeliz) |

### Tecnologías utilizadas
Python · Tkinter · Pillow · keyboard · Requests · PyInstaller · APIs REST (Groq, Gemini, OpenRouter) · OpenCode · Antigravity IDE

- **Creación:** 19 de marzo de 2026
- **Última actualización:** 23 de agosto de 2026

---

⚠️ Herramienta educativa: úsala bajo tu propio criterio y respeta las normas de tu institución.
