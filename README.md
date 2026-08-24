🇪🇸 **Español** · [🇺🇸 English](README.en.md)

# 🎯 Test Solver AI v1.0.2 — Linux

Versión de Test Solver AI para **Linux** (X11 y Wayland).

---

## 🚀 Uso rápido (ejecutable)

1. Descarga `test_solver_v1.0.2` desde el Release oficial v1.0.2 — Linux.
2. Dale permisos de ejecución y ejecútalo con **sudo** (necesario para los
   atajos globales de teclado):

   ```bash
   chmod +x test_solver_v1.0.2
   sudo ./test_solver_v1.0.2
   ```

   > 💡 **Alternativa sin `sudo` ni contraseñas**: añade tu usuario al grupo
   > `input`, cierra sesión y vuelve a entrar:
   >
   > ```bash
   > sudo usermod -aG input $USER
   > ```
   >
   > Después podrás lanzar la app directamente desde tu usuario — incluso con
   > doble click desde un lanzador `.desktop` del escritorio.

3. Si falta la clave del proveedor actual, se abrirá **Configuración**
   automáticamente.
4. Pega tu clave API (se guarda **solo localmente**, junto al binario).
5. Pulsa **Iniciar servicio** y usa **F8** sobre cualquier pregunta de tu
   examen online.

> El cierre de la ventana lo deja minimizado al fondo; usa **Salir** o **F9**
> para terminar de verdad.

## 🔑 Permisos y sesión gráfica en Linux

- **Atajos globales**: la librería `keyboard` lee `/dev/input` directamente,
  por lo que se necesitan privilegios: ejecuta con `sudo`, o añade tu usuario
  al grupo `input` (`sudo usermod -aG input $USER`, cierra sesión y vuelve a
  entrar) para lanzarla como usuario normal. Sin ellos, el botón
  *Iniciar servicio* mostrará un error explicativo.
- **Captura de pantalla**:
  - En **X11** funciona automáticamente (Pillow/XCB, o `scrot`/`maim` si
    están instalados).
  - En **Wayland** se usan herramientas nativas si están disponibles:
    `grim` (Sway/wlroots), `gnome-screenshot` (GNOME) o `spectacle` (KDE).
    Instala la de tu escritorio si la captura falla, p. ej.:
    `sudo apt install grim` / `sudo pacman -S grim`.

## 🛠️ Ejecutar desde código fuente

```bash
cd code_source_v1.0.2
pip install -r requirements.txt
sudo python3 test_solver_v1.0.2.py
```

Requisitos: Python 3.10+, Tkinter (incluido en `python3-tk` en Debian/Ubuntu),
pantalla ≥ 1280x720 recomendada.

## 📦 Construir el ejecutable

```bash
cd code_source_v1.0.2
./build_linux.sh
# resultado en dist/test_solver_v1.0.2
```

o manualmente:

```bash
python3 -m PyInstaller test_solver_v1.0.2.spec --noconfirm --clean
```

## ⚙️ Configuración

- El archivo `config.json` se crea **junto al binario/script** (nunca en rutas
  relativas al sistema). Plantilla limpia:
  [`config.example.json`](code_source_v1.0.2/config.example.json).
- Desde **Configuración** puedes cambiar proveedor, clave, endpoint, modelo,
  idioma y hotkeys; todo se aplica en caliente si el servicio está corriendo.
- La fuente Open Sans incluida se instala a nivel de usuario
  (`~/.local/share/fonts/TestSolverAI`) al primer arranque; si no está
  disponible se usa la fuente del sistema más cercana.

## 🗂️ Estructura

```
├── code_source_v1.0.2/     # Código fuente + spec de PyInstaller (Linux)
│   ├── media/fonts/        # Open Sans (SIL OFL)
│   ├── requirements.txt    # Dependencias de Python
│   ├── build_linux.sh      # Script de construcción del binario
│   ├── config.example.json # Plantilla limpia de configuración
│   ├── test_solver_v1.0.2.spec
│   └── test_solver_v1.0.2.py
├── media/                  # Iconos del proyecto
├── README.md               # Documentación (Español)
└── README.en.md            # Documentation (English)
```

---

⚠️ Herramienta educativa: úsala bajo tu propio criterio y respeta las normas de tu institución.
