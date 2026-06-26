#!/usr/bin/env python3
"""
ATW-622G (Telmex) backup config decryptor — 100% local, terminal UI.

Decrypts XOR-encrypted .xml backups and extracts PPPoE / web panel credentials.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# XOR key: ASCII "tecomtce"
XOR_KEY = bytes([0x74, 0x65, 0x63, 0x6F, 0x6D, 0x74, 0x65, 0x63])

VALIDATION_MARKERS = ("pppUser", "SUSER_NAME")

VALUE_RE = re.compile(
    r'<Value\s+Name="([^"]+)"\s+Value="([^"]*)"\s*/?>',
    re.IGNORECASE,
)
CONFIG_BLOCK_RE = re.compile(
    r'<Config\s+Name="([^"]+)"[^>]*>(.*?)</Config>',
    re.IGNORECASE | re.DOTALL,
)

# ── ANSI palette (dark terminal / hack aesthetic) ─────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[38;5;46m"
CYAN = "\033[38;5;51m"
MAGENTA = "\033[38;5;201m"
YELLOW = "\033[38;5;226m"
RED = "\033[38;5;196m"
GRAY = "\033[38;5;245m"
BG_PANEL = "\033[48;5;235m"
MONO = "\033[38;5;252m"

SPLASH_SECONDS = 3.0
PROJECT_LINK = None  # pending
IGNORED_XML_NAMES = frozenset({""})

SPLASH_ART = f"""
{CYAN}
    ██████╗ ██╗   ██╗
    ██╔══██╗╚██╗ ██╔╝
    ██████╔╝ ╚████╔╝
    ██╔══██╗  ╚██╔╝
    ██████╔╝   ██║
    ╚═════╝    ╚═╝

███████╗██╗  ██╗██╗   ██╗██╗     ██╗███╗   ██╗███████╗
██╔════╝██║ ██╔╝╚██╗ ██╔╝██║     ██║████╗  ██║██╔════╝
███████╗█████╔╝  ╚████╔╝ ██║     ██║██╔██╗ ██║█████╗
╚════██║██╔═██╗   ╚██╔╝  ██║     ██║██║╚██╗██║██╔══╝
███████║██║  ██╗   ██║   ███████╗██║██║ ╚████║███████╗
╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝
{RESET}
{DIM}        ATW-622G Backup Decryptor · Telmex{RESET}
"""


def enable_windows_ansi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


@dataclass(frozen=True)
class ExtractedField:
    key: str
    label: str
    value: str


def xor_decrypt(data: bytes) -> bytes:
    key_len = len(XOR_KEY)
    return bytes(b ^ XOR_KEY[i % key_len] for i, b in enumerate(data))


def format_mac(raw: str) -> str:
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", raw)
    if len(cleaned) != 12:
        return raw
    pairs = [cleaned[i : i + 2].upper() for i in range(0, 12, 2)]
    return ":".join(pairs)


def parse_values(xml_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, value in VALUE_RE.findall(xml_text):
        values[name] = value
    return values


def find_wan_mac(xml_text: str, all_values: dict[str, str]) -> Optional[str]:
    for block_name, body in CONFIG_BLOCK_RE.findall(xml_text):
        if "wan" not in block_name.lower():
            continue
        for name, value in VALUE_RE.findall(body):
            if name.lower() == "macaddr":
                return value
    for name, value in all_values.items():
        if name.lower() == "macaddr":
            return value
    return None


def validate_backup(xml_text: str) -> None:
    if not any(marker in xml_text for marker in VALIDATION_MARKERS):
        raise ValueError(
            "El archivo no parece ser un backup ATW-622G válido "
            "(no se encontraron campos pppUser ni SUSER_NAME tras descifrar)."
        )


def extract_fields(xml_text: str) -> list[ExtractedField]:
    values = parse_values(xml_text)
    mac_raw = find_wan_mac(xml_text, values)

    fields = [
        ExtractedField("pppUser", "Usuario PPPoE", values.get("pppUser", "")),
        ExtractedField("pppPasswd", "Contraseña PPPoE", values.get("pppPasswd", "")),
        ExtractedField("SUSER_NAME", "Usuario panel web", values.get("SUSER_NAME", "")),
        ExtractedField(
            "SUSER_PASSWORD",
            "Contraseña panel web",
            values.get("SUSER_PASSWORD", ""),
        ),
        ExtractedField(
            "MacAddr",
            "MAC del dispositivo (WAN)",
            format_mac(mac_raw) if mac_raw else "",
        ),
    ]
    return fields


def read_backup(path: Path) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")
    if path.suffix.lower() != ".xml":
        raise ValueError("Se esperaba un archivo con extensión .xml")
    return path.read_bytes()


def decrypt_file(path: Path) -> tuple[str, list[ExtractedField]]:
    ciphertext = read_backup(path)
    plaintext = xor_decrypt(ciphertext)
    try:
        xml_text = plaintext.decode("utf-8")
    except UnicodeDecodeError:
        xml_text = plaintext.decode("latin-1")
    validate_backup(xml_text)
    return xml_text, extract_fields(xml_text)


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def xml_files_in_root() -> list[Path]:
    return sorted(
        path
        for path in app_root().glob("*.xml")
        if path.name.lower() not in IGNORED_XML_NAMES
    )


def should_close_terminal_on_exit() -> bool:
    if not sys.stdin.isatty():
        return False
    if not getattr(sys, "frozen", False):
        return False
    if sys.platform == "darwin":
        # SHLVL 1 = ventana nueva (doble clic); >1 = terminal ya abierta
        return int(os.environ.get("SHLVL", "1")) <= 1
    return True


def close_terminal_window() -> None:
    if sys.platform == "darwin":
        for script in (
            'tell application "Terminal" to close front window',
            'tell application "iTerm" to close current window',
        ):
            subprocess.run(["osascript", "-e", script], check=False)
    elif sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.FreeConsole()  # type: ignore[attr-defined]
        except Exception:
            pass


def finish_program(message: str = "Hasta pronto.") -> int:
    clear_screen()
    print(f"  {DIM}{message}{RESET}\n")
    if should_close_terminal_on_exit():
        time.sleep(1.5)
        close_terminal_window()
    return 0


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")


def show_splash(duration: float = SPLASH_SECONDS) -> None:
    clear_screen()
    print(SPLASH_ART)
    time.sleep(duration)
    clear_screen()


def fields_to_text(fields: list[ExtractedField], source: Path) -> str:
    lines = [
        "ATW-622G Backup — datos descifrados",
        f"Origen: {source.name}",
        "",
    ]
    for field in fields:
        value = field.value or "(no encontrado)"
        lines.append(f"{field.label}: {value}")
    return "\n".join(lines) + "\n"


def ask_save_txt(fields: list[ExtractedField], source: Path) -> None:
    try:
        answer = input(
            f"  {CYAN}¿Guardar en archivo .txt? (s/n):{RESET} "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if answer not in ("s", "si", "sí", "y", "yes"):
        return

    default_name = f"{source.stem}_decrypted.txt"
    try:
        out_raw = input(
            f"  {DIM}Nombre del archivo [{default_name}]:{RESET} "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    out_name = out_raw or default_name
    if not out_name.lower().endswith(".txt"):
        out_name += ".txt"

    out_path = app_root() / out_name
    try:
        out_path.write_text(fields_to_text(fields, source), encoding="utf-8")
        print(f"  {GREEN}✓ Guardado en:{RESET} {out_path}")
    except OSError as exc:
        print(f"  {RED}✗ No se pudo guardar:{RESET} {exc}")


def resolve_xml_path() -> Optional[Path]:
    while True:
        local = xml_files_in_root()

        if local:
            print(f"  {DIM}Archivos .xml en carpeta del programa:{RESET}")
            for index, path in enumerate(local, start=1):
                print(f"    {MAGENTA}[{index}]{RESET} {path.name}")
            print(f"    {DIM}Escribe la ruta, el número, o {RESET}{MAGENTA}q{DIM} para cancelar.{RESET}")
        else:
            print(f"  {DIM}No hay archivos .xml en la carpeta del programa.{RESET}")
            print(f"  {DIM}Coloca el backup aquí o escribe la ruta completa.{RESET}")
            print(f"  {DIM}Escribe {RESET}{MAGENTA}q{DIM} para cancelar.{RESET}")
        print()

        default_hint = f" [{local[0].name}]" if len(local) == 1 else ""
        try:
            raw = input(
                f"  {CYAN}Ruta del archivo .xml{default_hint}:{RESET} "
            ).strip().strip("'\"")
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        if raw.lower() in ("q", "salir", "cancelar"):
            return None

        if not raw:
            if len(local) == 1:
                return local[0]
            print(f"  {YELLOW}! Debes indicar la ruta del backup .xml.{RESET}")
            print()
            continue

        if raw.isdigit() and local:
            picked = int(raw)
            if 1 <= picked <= len(local):
                return local[picked - 1]
            print(f"  {YELLOW}! Número fuera de rango.{RESET}")
            print()
            continue

        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (app_root() / path).resolve()
        else:
            path = path.resolve()

        if not path.is_file():
            print(f"  {RED}✗ No se encontró el archivo:{RESET} {path}")
            print()
            continue
        if path.suffix.lower() != ".xml":
            print(f"  {RED}✗ Se esperaba un archivo con extensión .xml{RESET}")
            print()
            continue
        return path


# ── Terminal UI ───────────────────────────────────────────────────────────────

def hr(char: str = "─", width: int = 62) -> str:
    return f"{GRAY}{char * width}{RESET}"


def banner() -> None:
    print()
    print(f"{GREEN}╔{'═' * 60}╗{RESET}")
    print(f"{GREEN}║{RESET} {BOLD}{CYAN}ATW-622G BACKUP DECRYPTOR{RESET}{' ' * 34}{GREEN}║{RESET}")
    print(f"{GREEN}║{RESET} {DIM}Telmex · XOR local · sin red{RESET}{' ' * 30}{GREEN}║{RESET}")
    print(f"{GREEN}╚{'═' * 60}╝{RESET}")
    print()


def print_field(index: int, field: ExtractedField) -> None:
    display = field.value if field.value else f"{RED}(no encontrado){RESET}"
    label_pad = 26
    print(f"  {BG_PANEL} {MAGENTA}[{index}]{RESET} {CYAN}{field.label:<{label_pad}}{RESET} ")
    print(f"      {MONO}{BOLD}{display}{RESET}")
    print()


def print_results(fields: list[ExtractedField], source: Path) -> None:
    banner()
    print(f"  {DIM}Archivo:{RESET} {source.name}")
    print(f"  {hr()}")
    print()
    for index, field in enumerate(fields, start=1):
        print_field(index, field)
    print(f"  {hr()}")
    print()


def show_main_menu() -> None:
    clear_screen()
    print()
    print(f"{GREEN}╔{'═' * 40}╗{RESET}")
    print(f"{GREEN}║{RESET} {BOLD}{CYAN}MENÚ PRINCIPAL{RESET}{' ' * 24}{GREEN}║{RESET}")
    print(f"{GREEN}╚{'═' * 40}╝{RESET}")
    print()
    print(f"  {MAGENTA}[1]{RESET} Desencriptar")
    print(f"  {MAGENTA}[2]{RESET} Link de proyecto {DIM}(pendiente){RESET}")
    print(f"  {MAGENTA}[3]{RESET} Salir")
    print()


def show_decrypt_prompt() -> None:
    clear_screen()
    print()
    print(f"{GREEN}╔{'═' * 40}╗{RESET}")
    print(f"{GREEN}║{RESET} {BOLD}{CYAN}DESENCRIPTAR{RESET}{' ' * 27}{GREEN}║{RESET}")
    print(f"{GREEN}╚{'═' * 40}╝{RESET}")
    print()


def show_project_link_screen() -> None:
    clear_screen()
    print()
    print(f"{GREEN}╔{'═' * 40}╗{RESET}")
    print(f"{GREEN}║{RESET} {BOLD}{CYAN}LINK DE PROYECTO{RESET}{' ' * 21}{GREEN}║{RESET}")
    print(f"{GREEN}╚{'═' * 40}╝{RESET}")
    print()
    if PROJECT_LINK:
        print(f"  {CYAN}Proyecto:{RESET} {PROJECT_LINK}")
    else:
        print(f"  {YELLOW}Link de proyecto:{RESET} {DIM}pendiente de poner{RESET}")
    print()


def pause(message: str = "Presiona Enter para continuar...") -> None:
    try:
        input(f"  {DIM}{message}{RESET}")
    except (EOFError, KeyboardInterrupt):
        print()


def run_decrypt_flow(path: Path, *, ask_save: bool = True) -> int:
    clear_screen()
    try:
        _, fields = decrypt_file(path)
    except (OSError, ValueError) as exc:
        print(f"\n  {RED}ERROR:{RESET} {exc}\n")
        return 1

    print_results(fields, path)
    if ask_save and sys.stdin.isatty():
        print()
        ask_save_txt(fields, path)
    return 0


def main_menu_loop() -> int:
    while True:
        show_main_menu()
        try:
            choice = input(f"  {GREEN}>{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if choice in ("3", "q", "salir", "exit"):
            return finish_program()

        if choice == "1":
            while True:
                show_decrypt_prompt()
                path = resolve_xml_path()
                if path is None:
                    print(f"  {YELLOW}Operación cancelada.{RESET}")
                    pause()
                    break
                if run_decrypt_flow(path) == 0:
                    pause("Presiona Enter para volver al menú...")
                    break
                pause("Presiona Enter para intentar otra ruta...")
            continue

        if choice == "2":
            show_project_link_screen()
            pause()
            continue

        clear_screen()
        print(f"  {YELLOW}? Opción no válida.{RESET}")
        pause()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Descifra backups .xml del router ATW-622G (Telmex).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python atw622g_decrypt.py              # menú interactivo\n"
            "  python atw622g_decrypt.py backup.xml   # descifrar directo\n"
            "  ./atw622g-decrypt backup.xml -q        # sin preguntar guardar .txt\n"
        ),
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Ruta al archivo .xml cifrado",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Solo mostrar campos, sin preguntar guardar .txt",
    )
    parser.add_argument(
        "--dump-xml",
        action="store_true",
        help="Imprimir XML descifrado completo (stdout)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    enable_windows_ansi()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dump_xml:
        if args.file is None:
            print("ERROR: se requiere un archivo .xml", file=sys.stderr)
            return 2
        try:
            xml_text, _ = decrypt_file(args.file)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(xml_text)
        return 0

    interactive = sys.stdin.isatty()
    if interactive:
        show_splash()

    if args.file is not None:
        return run_decrypt_flow(
            args.file,
            ask_save=interactive and not args.quiet,
        )

    if not interactive:
        parser.print_help()
        return 2

    return main_menu_loop()


if __name__ == "__main__":
    raise SystemExit(main())
