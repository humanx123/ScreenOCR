# ScreenOCR

App de escritorio para Windows: captura un área de la pantalla, extrae el texto con OCR (inglés y español) y lo deja editable en un dashboard.

## Descargar (gratis)

**[⬇ ScreenOCR-Setup-1.0.0.exe](https://github.com/osram90/ScreenOCR/releases/latest)** — instalador para Windows 10/11 (sin permisos de administrador). Incluye acceso directo en el menú Inicio, opción de escritorio y desinstalador.

Motor local de Windows: para inglés instala el paquete OCR una vez, como administrador:
`Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'`

## Apoyar el proyecto

ScreenOCR es gratis. Si te sirve, puedes hacer una donación voluntaria (también desde el botón **Donar** de la app):

- **BTC:** `bc1qd9j45f4t0jwyhjhqh2kvz2cr7k8xye460rr2y7`
- **XMR:** `447gTj6Hg6gaAEAUmjqfhqDZr1PziUTvbT4LYLpmLVnTNVFK6cqeqPfh6P4neMKLWX5jDXAr94fWHacJwDvjmCzBBH8wPBt`
- **USDC (Arbitrum):** `0xAC43f9b0E7F0ae6386cfC8ef6BFf62CE9c3006A1`

## Compilar desde código

```powershell
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name ScreenOCR --icon icon.ico --collect-all winrt main.py
ISCC.exe installer.iss   # Inno Setup 6 -> installer\ScreenOCR-Setup-1.0.0.exe
```

## Instalación

```powershell
cd C:\Users\fidel\ScreenOCR
pip install -r requirements.txt
python main.py
```

## Uso

1. **Ctrl+Shift+S** (o el botón *Nueva captura*) → arrastra sobre la pantalla. `Esc` o clic derecho cancela.
2. La captura se guarda como trabajo y el OCR se ejecuta en segundo plano.
3. Columna izquierda: trabajos con botones ✎ (renombrar) y ✕ (eliminar).
4. Panel derecho: captura arriba y texto editable debajo. `Ctrl+S` o *Guardar* para conservar cambios; *Copiar* al portapapeles; *Reintentar OCR* si hubo error.

## Motores de OCR

En *Configuración* eliges el motor:

- **OCR.space (nube, gratis)**: plan gratuito, motor 2, ~25 000 solicitudes/mes, máximo 1 MB por imagen.
  Para tu propia clave: https://ocr.space/ocrapi/freekey → pégala en *Configuración*.
- **Windows (local, sin internet)**: usa el OCR integrado de Windows; no tiene límites ni necesita clave.
  Lee los paquetes OCR instalados en el sistema. Hoy tienes **español** (es-ES, es-MX).
  Para inglés, ejecuta PowerShell **como administrador**:

  ```powershell
  Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'
  ```

En ambos motores, *Automático (EN + ES)* detecta el idioma; también puedes forzar *Inglés* o *Español*.

Los datos se guardan en `%APPDATA%\ScreenOCR` (base SQLite `jobs.db`, carpeta `images\`, y `config.json`).
