# ATW-Decrypt

Herramienta de terminal para descifrar backups `.xml` exportados desde routers **ATW-622G** de Telmex. Extrae credenciales PPPoE, acceso al panel web y la MAC WAN del dispositivo.

## Compatibilidad

| Estado | Detalle |
|--------|---------|
| **Probado y aprobado** | Modelo **ATW-622G** con proveedor **Telmex** |
| **Posible compatibilidad** | Otros modelos de la misma marca que usen el mismo formato de backup cifrado (XOR). No garantizado — úsalo bajo tu propia responsabilidad |

> Esta herramienta fue desarrollada y validada con backups reales del ATW-622G en red Telmex. Si tienes otro modelo o ISP, el descifrado puede fallar o mostrar datos incompletos.

## Requisitos

- **Script Python:** Python 3.8 o superior (solo biblioteca estándar en ejecución)
- **Binario:** No requiere Python instalado
- **Compilar binario:** Python 3 + PyInstaller (se instala automáticamente con los scripts de build)

## Datos que extrae

| Campo | Descripción |
|-------|-------------|
| Usuario PPPoE | Credencial de conexión a internet |
| Contraseña PPPoE | Contraseña de conexión PPPoE |
| Usuario panel web | Acceso al administrador del router |
| Contraseña panel web | Contraseña del panel |
| MAC WAN | Dirección MAC de la interfaz WAN |

---

## Uso con el script Python

### 1. Descargar el backup del router

Desde el panel del ATW-622G, exporta la configuración como archivo `.xml`.

### 2. Colocar el archivo

Copia el backup `.xml` en la **misma carpeta** donde está `atw622g_decrypt.py`.

### 3. Ejecutar

```bash
python3 atw622g_decrypt.py
```

Verás un splash de inicio y el menú principal:

```
[1] Desencriptar
[2] Link de proyecto (pendiente)
[3] Salir
```

### 4. Desencriptar

1. Elige la opción **1**
2. Si hay un `.xml` en la carpeta, aparecerá en la lista — escribe el número o la ruta
3. Si no hay archivos, escribe la ruta completa del backup
4. Revisa los datos mostrados
5. Responde **s** si quieres guardar un `.txt` con los resultados

### Uso directo (sin menú)

```bash
# Descifrar un archivo concreto
python3 atw622g_decrypt.py /ruta/al/backup.xml

# Solo mostrar resultados, sin preguntar guardar .txt
python3 atw622g_decrypt.py backup.xml -q

# Ver el XML descifrado completo
python3 atw622g_decrypt.py backup.xml --dump-xml
```

---

## Uso con el binario

### macOS / Linux

1. Compila (o descarga el binario de Releases):

   ```bash
   ./build.sh
   ```

2. Copia tu backup `.xml` en la carpeta `dist/` (junto a `atw622g-decrypt`)

3. Ejecuta:

   ```bash
   ./dist/atw622g-decrypt
   ```

   También puedes abrirlo con doble clic o arrastrar el `.xml` al terminal:

   ```bash
   ./dist/atw622g-decrypt /ruta/al/backup.xml
   ```

### Windows

1. Compila:

   ```cmd
   build.bat
   ```

2. Coloca el backup `.xml` en `dist\` junto a `atw622g-decrypt.exe`

3. Ejecuta `dist\atw622g-decrypt.exe` o desde CMD:

   ```cmd
   dist\atw622g-decrypt.exe backup.xml
   ```

> El binario solo busca archivos `.xml` en su propia carpeta (`dist/`). El script solo busca en la carpeta donde está `atw622g_decrypt.py`.

---

## Compilar el ejecutable

### macOS / Linux

```bash
chmod +x build.sh
./build.sh
```

Genera: `dist/atw622g-decrypt`

### Windows

```cmd
build.bat
```

Genera: `dist\atw622g-decrypt.exe`

Los scripts crean un entorno virtual `.venv`, instalan PyInstaller y producen un ejecutable de un solo archivo.

---

## Atajos del menú interactivo

| Tecla | Acción |
|-------|--------|
| `1` | Desencriptar backup |
| `2` | Link del proyecto |
| `3` / `q` | Salir |
| `1`, `2`… | Elegir archivo de la lista (pantalla Desencriptar) |
| `q` | Cancelar selección de archivo |

---

## Solución de problemas

**"El archivo no parece ser un backup ATW-622G válido"**
- El archivo no es un backup cifrado de este router, está corrupto o corresponde a otro modelo/ISP.

**No aparece mi `.xml` en la lista**
- Debe estar en la misma carpeta que el script o el binario, según cómo lo ejecutes.

**Error al compilar en macOS (Homebrew)**
- Usa `./build.sh`; crea un `.venv` local y evita el error `externally-managed-environment`.

---

## Estructura del proyecto

```
ATW-Decrypt/
├── atw622g_decrypt.py   # Script principal
├── build.sh               # Build macOS / Linux
├── build.bat              # Build Windows
├── .gitignore
└── README.md
```

---

## Autor

**By Skyline**

---

## Aviso legal

Usa esta herramienta únicamente sobre backups de equipos que te pertenezcan o para los que tengas autorización. El autor no se hace responsable del uso indebido.
