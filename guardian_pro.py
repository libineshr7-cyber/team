#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          GUARDIAN PRO — UNIFIED ENTRY POINT                  ║
║          File    : guardian_pro.py                           ║
╚══════════════════════════════════════════════════════════════╝

Single command-line launcher for all Guardian Pro modes:

  [1]  Web Dashboard      — browser-based security dashboard
  [2]  CLI Demo           — terminal walkthrough of all features
  [3]  Interactive Login  — manual login shell (login.py direct)
  [4]  Attack Simulator   — run brute-force attack only
"""

import sys
import os


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

class C:
    _on = os.isatty(1)
    _w  = staticmethod(lambda c, t: f"\033[{c}m{t}\033[0m" if C._on else t)
    cyan   = staticmethod(lambda t: C._w("96", t))
    green  = staticmethod(lambda t: C._w("92", t))
    yellow = staticmethod(lambda t: C._w("93", t))
    red    = staticmethod(lambda t: C._w("91", t))
    bold   = staticmethod(lambda t: C._w("1",  t))
    dim    = staticmethod(lambda t: C._w("2",  t))

DIV = "═" * 60


def banner() -> None:
    print(f"\n{DIV}")
    print(C.bold(C.cyan("  ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ ██╗ █████╗ ███╗")))
    print(C.bold(C.cyan("  GUARDIAN PRO — CYBERSECURITY EDUCATIONAL SUITE v2.0")))
    print(f"{DIV}\n")
    print(f"  Select an operation mode:\n")
    print(f"  {C.cyan('[1]')}  {C.bold('Web Dashboard')}     → Browser UI with live vault & attack sim")
    print(f"  {C.cyan('[2]')}  {C.bold('Full CLI Demo')}     → Guided terminal walkthrough")
    print(f"  {C.cyan('[3]')}  {C.bold('Interactive Login')} → Manual login shell for quick testing")
    print(f"  {C.cyan('[4]')}  {C.bold('Attack Simulator')}  → Standalone brute-force run")
    print(f"  {C.cyan('[5]')}  {C.bold('Exit')}\n")


# ══════════════════════════════════════════════════════════════
#  MODE HANDLERS
# ══════════════════════════════════════════════════════════════

def launch_web() -> None:
    try:
        import server
        import uvicorn
        print(f"\n{C.green('[*]')} Guardian Pro Web Dashboard → http://localhost:8080")
        print(C.dim("     Press Ctrl-C to stop.\n"))
        uvicorn.run(server.app, host="0.0.0.0", port=8080, log_level="warning")
    except ImportError as exc:
        print(C.red(f"[!] Missing dependency: {exc}"))
        print(C.dim("    Install with: pip install uvicorn starlette"))


def launch_demo() -> None:
    try:
        import run_demo
        run_demo.main()
    except ImportError:
        print(C.red("[!] run_demo.py not found."))


def launch_login() -> None:
    try:
        import login as lg
        import runpy
        runpy.run_module("login", run_name="__main__", alter_sys=True)
    except ImportError:
        print(C.red("[!] login.py not found."))


def launch_brute() -> None:
    try:
        import login
        import brute
        login.initialize_system()
        result = brute.brute_force_attack()
        brute.display_attack_statistics()
        outcome = C.green("SUCCESS") if result else C.red("DEFENDED")
        print(f"[*] Attack outcome: {outcome}")
    except ImportError as exc:
        print(C.red(f"[!] Missing module: {exc}"))


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

DISPATCH = {
    "1": launch_web,
    "2": launch_demo,
    "3": launch_login,
    "4": launch_brute,
}


def main() -> None:
    while True:
        banner()
        try:
            choice = input("  Selection > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Shutdown.")
            sys.exit(0)

        if choice == "5":
            print("[*] Goodbye.\n")
            sys.exit(0)

        handler = DISPATCH.get(choice)
        if handler:
            handler()
        else:
            print(C.yellow("[!] Invalid selection — please enter 1–5.\n"))


if __name__ == "__main__":
    main()
