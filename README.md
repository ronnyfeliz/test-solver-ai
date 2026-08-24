# 🎯 Test Solver AI

Herramienta de escritorio **multiplataforma** que analiza preguntas de opción múltiple
en tu pantalla usando IA de visión y muestra la respuesta al instante en un
overlay flotante.

> **F8** → captura y analiza la pantalla · **F9** → cierra la aplicación

---

## ✨ Características

- **Análisis con un solo hotkey**: captura optimizada de pantalla → LLM de visión → respuesta explicada.
- **Overlay flotante** siempre visible con vistas de carga / resultado / error, copiar respuesta y reintentar.
- **Panel principal** con estado real del servicio, tiempo activo, última verificación e info del proveedor/modelo.
- **Máquina de estados real**: estados `detenido / iniciando / ejecución / deteniendo / caído` sondeados desde el hook real del sistema, con watchdog que detecta caídas y permite recuperar el servicio.
- **Multi-proveedor extensible** con niveles gratuitos reales.
- **Bilingüe ES/EN completo**, aplicado en vivo sin reiniciar.
- Tipografía **Open Sans** incrustada (no requiere instalación) y botones redondeados modernos.
- Notificaciones toast, instancia única, configuración persistente local.

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

## 📦 Plataformas

| Plataforma | Estado | Documentación | Descarga |
|---|---|---|---|
| **Windows** | ✅ v1.0.2 | [`Windows/Test-solver-v1.0.2/README.md`](Windows/Test-solver-v1.0.2/README.md) | [⬇️ Release v1.0.2](https://github.com/ronnyfeliz/test-solver-ai/releases/tag/windows-v1.0.2) |
| **Linux** | 🚧 Próximamente | — | — |

Cada carpeta de plataforma contiene su código fuente, instrucciones de
instalación/ejecución y el proceso de empaquetado específico.

## 🔒 Seguridad y privacidad

- Ninguna credencial está hardcodeada en el código fuente.
- Las claves API se guardan **solo localmente** (nunca se envían a los logs: cualquier error se sanitiza antes de mostrarse).
- Este repositorio excluye mediante `.gitignore`: `config.json`, logs, binarios de compilación, respaldos internos y notas personales.
- Si alguna vez filtraste una clave (p. ej. en un respaldo antiguo), **revócala** en el panel de tu proveedor antes de publicar.

## 👥 Créditos

| Rol | Persona |
|---|---|
| **Autor original y creador de la aplicación** | **Alex Hatton** |
| **Colaborador GUI** (interfaz gráfica moderna, arquitectura y empaquetado) | **Ronny Feliz** · [github.com/ronnyfeliz](https://github.com/ronnyfeliz) |

### Tecnologías utilizadas
Python · Tkinter · Pillow · keyboard · Requests · PyInstaller · APIs REST (Groq, Gemini, OpenRouter) · OpenCode · Antigravity IDE

- **Creación:** 19 de marzo de 2026
- **Última actualización:** 24 de agosto de 2026

## 💼 Colaborador / Desarrollador — Ronny Feliz

Responsable del desarrollo de la interfaz gráfica moderna, la arquitectura
y el empaquetado de Test Solver AI.

| Contacto | Enlace |
|---|---|
| 🌐 Portafolio | [ronnyfeliz.github.io](https://ronnyfeliz.github.io/) |
| 🐙 GitHub | [@ronnyfeliz](https://github.com/ronnyfeliz) |
| 💼 LinkedIn | [in/ronnyfeliz2](https://www.linkedin.com/in/ronnyfeliz2/) |
| ✉️ Correo | [blxst608@gmail.com](mailto:blxst608@gmail.com) |

---

⚠️ Herramienta educativa: úsala bajo tu propio criterio y respeta las normas de tu institución.
