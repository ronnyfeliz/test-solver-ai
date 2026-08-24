# 🎯 Test Solver AI v1.0.2 — Windows

Versión de Test Solver AI para **Windows 10/11**.

> Documentación general del proyecto (características, proveedores de IA
> soportados, seguridad y créditos): [README principal](../../README.md)

---

## 🚀 Uso rápido (ejecutable)

1. Descarga `test_solver_v1.0.2.exe` (ver [Releases](../../releases)).
2. Ejecútalo como administrador: si falta la clave del proveedor actual, se abrirá **Ajustes** automáticamente.
3. Pega tu clave API (se guarda **solo localmente**, junto al exe).
4. Pulsa **Iniciar servicio** y usa **F8** sobre cualquier pregunta de tu examen online.

> El cierre de la ventana lo deja minimizado al fondo; usa **Salir** o **F9** para terminar de verdad.
> Verifica en el Administrador de tareas que el servicio esté en ejecución antes de usar el hotkey.

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

## 🗂️ Estructura

```
├── code_source_v1.0.2/     # Código fuente + spec de PyInstaller
│   ├── media/fonts/        # Open Sans (SIL OFL)
│   ├── config.example.json # Plantilla limpia de configuración
│   └── test_solver_v1.0.2.py
├── media/                  # Iconos del proyecto
└── README.md               # Documentación de la versión Windows
```

---

⚠️ Herramienta educativa: úsala bajo tu propio criterio y respeta las normas de tu institución.
