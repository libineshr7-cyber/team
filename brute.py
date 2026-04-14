#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          GUARDIAN PRO — SECURE FILE SYSTEM                   ║
║          Module : brute.py  (Attacker / Red Team)            ║
║          Author : Cybersecurity Student                       ║
║          Course : Introduction to Cybersecurity              ║
╚══════════════════════════════════════════════════════════════╝

PURPOSE
───────
Simulates an automated brute-force attack against the Guardian
login system. The attacker methodically tries every numeric
combination from 000 → 999, stopping as soon as:
  • The correct password is found  → ATTACK SUCCESSFUL
  • The defender's threshold fires → SYSTEM SELF-DESTRUCTS
  • All combinations are exhausted → PASSWORD OUT OF RANGE

EDUCATIONAL VALUE
─────────────────
Brute force is the most primitive attack vector — yet it succeeds
every time when the password space is small enough and no rate-
limiting or lockout policy exists. This simulation makes both
the attack mechanics and the defender's countermeasures visible
in real time.

⚠  LEGAL NOTICE
───────────────
Run ONLY on systems you own or have explicit written permission
to test. Unauthorised access is a criminal offence in virtually
every jurisdiction (CFAA, Computer Misuse Act, IT Act 2000 …).
"""

import time
from datetime import datetime
from typing import Generator, Optional

import login  # The target / defender module

# ══════════════════════════════════════════════════════════════
#  ATTACK CONFIGURATION
# ══════════════════════════════════════════════════════════════

# Numeric password search space (inclusive on both ends)
PASSWORD_MIN: int = 0
PASSWORD_MAX: int = 999

# Inter-attempt delay (seconds).  0 = maximum speed; 0.1 keeps output readable.
ATTACK_DELAY: float = 0.1

# ══════════════════════════════════════════════════════════════
#  TERMINAL COLOURS  (mirrors login.py's helper)
# ══════════════════════════════════════════════════════════════

import os

class Color:
    _enabled = os.isatty(1)

    @staticmethod
    def _w(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if Color._enabled else text

    red    = staticmethod(lambda t: Color._w("91", t))
    green  = staticmethod(lambda t: Color._w("92", t))
    yellow = staticmethod(lambda t: Color._w("93", t))
    cyan   = staticmethod(lambda t: Color._w("96", t))
    bold   = staticmethod(lambda t: Color._w("1",  t))
    dim    = staticmethod(lambda t: Color._w("2",  t))

_DIV = "═" * 60
_BANG = "!" * 60


# ══════════════════════════════════════════════════════════════
#  PASSWORD GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_passwords() -> Generator[str, None, None]:
    """
    Yield every zero-padded 3-digit candidate in ascending order.

    Example output sequence: "000", "001", "002", …, "999"

    Using a generator keeps memory usage constant — the entire
    candidate list is never loaded into RAM simultaneously.
    This mirrors how real attack tools handle giant wordlists.
    """
    for num in range(PASSWORD_MIN, PASSWORD_MAX + 1):
        yield str(num).zfill(3)


# ══════════════════════════════════════════════════════════════
#  MAIN ATTACK LOOP
# ══════════════════════════════════════════════════════════════

def brute_force_attack() -> bool:
    """
    Execute the brute-force attack and return the outcome.

    Returns:
        True  — password cracked, vault contents displayed.
        False — attack defeated (system locked or file destroyed).
    """
    total_candidates = PASSWORD_MAX - PASSWORD_MIN + 1

    # ── Banner ─────────────────────────────────────────────────
    print(f"\n{Color.red(_DIV)}")
    print(Color.red(Color.bold("  🔓  BRUTE FORCE ATTACK SIMULATOR")))
    print(f"{Color.red(_DIV)}\n")

    # ── Initialise the defender ────────────────────────────────
    print("[*] Booting target system…")
    login.initialize_system()

    print(f"\n{Color.cyan('[*]')} Attack parameters:")
    print(f"    Search space   : {PASSWORD_MIN:03d} → {PASSWORD_MAX:03d}")
    print(f"    Candidates     : {total_candidates:,}")
    print(f"    Inter-attempt  : {ATTACK_DELAY}s")
    print(f"    Started at     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n[*] Commencing attack…\n{_DIV}\n")

    start_time   = time.perf_counter()
    attempt_num  = 0

    for password in generate_passwords():
        attempt_num += 1

        # Progress indicator every 50 attempts to reduce noise
        if attempt_num % 50 == 0 or attempt_num <= 5:
            pct = attempt_num / total_candidates * 100
            bar_filled = int(pct / 5)
            bar = "█" * bar_filled + "░" * (20 - bar_filled)
            print(f"  [{bar}] {pct:5.1f}%  |  Trying: {password}  |  #{attempt_num}")
        else:
            print(Color.dim(f"  [Attempt #{attempt_num:>4}] → {password}"), end="\r")

        # ── Check defender state BEFORE the attempt ────────────
        if login.system_locked:
            return _report_failure(
                reason="SYSTEM LOCKED — SELF-DESTRUCT TRIGGERED",
                detail="The defender detected the intrusion and wiped the vault.",
                attempt_num=attempt_num,
                elapsed=time.perf_counter() - start_time,
            )

        if not login.os.path.exists(login.PROTECTED_FILE):
            return _report_failure(
                reason="TARGET FILE ALREADY DESTROYED",
                detail="The protected file was deleted before the password was found.",
                attempt_num=attempt_num,
                elapsed=time.perf_counter() - start_time,
            )

        # ── Attempt authentication ─────────────────────────────
        if login.check_password(password):
            return _report_success(password, attempt_num, time.perf_counter() - start_time)

        # Rate-limit sleep (attacker-side delay for readability)
        if ATTACK_DELAY > 0:
            time.sleep(ATTACK_DELAY)

    # ── Exhausted entire search space ──────────────────────────
    return _report_failure(
        reason="PASSWORD OUTSIDE SEARCH RANGE",
        detail=f"All {attempt_num:,} candidates tried — password not in {PASSWORD_MIN:03d}–{PASSWORD_MAX:03d}.",
        attempt_num=attempt_num,
        elapsed=time.perf_counter() - start_time,
    )


# ══════════════════════════════════════════════════════════════
#  RESULT REPORTERS
# ══════════════════════════════════════════════════════════════

def _report_success(password: str, attempts: int, elapsed: float) -> bool:
    print(f"\n\n{Color.green(_DIV)}")
    print(Color.green(Color.bold("  ✓  ATTACK SUCCESSFUL — VAULT BREACHED")))
    print(f"{Color.green(_DIV)}")
    print(Color.green(f"  Correct password : {Color.bold(password)}"))
    print(Color.green(f"  Attempts needed  : {attempts:,}"))
    print(Color.green(f"  Time elapsed     : {elapsed:.2f}s"))
    print(Color.green(f"  Avg per attempt  : {elapsed / attempts:.4f}s"))
    print(f"{Color.green(_DIV)}\n")

    print("[*] Retrieving vault contents…")
    login.display_file_contents()
    return True


def _report_failure(reason: str, detail: str, attempt_num: int, elapsed: float) -> bool:
    print(f"\n\n{Color.red(_BANG)}")
    print(Color.red(Color.bold(f"  ✗  ATTACK FAILED — {reason}")))
    print(f"{Color.red(_BANG)}")
    print(Color.red(f"  {detail}"))
    print(Color.red(f"  Attempts made    : {attempt_num:,}"))
    print(Color.red(f"  Time elapsed     : {elapsed:.2f}s"))
    print(f"{Color.red(_BANG)}\n")
    return False


# ══════════════════════════════════════════════════════════════
#  POST-ATTACK ANALYSIS
# ══════════════════════════════════════════════════════════════

def display_attack_statistics() -> None:
    """
    Print educational analysis of the attack's effectiveness and
    the defender's countermeasures.
    """
    total = PASSWORD_MAX - PASSWORD_MIN + 1
    worst_case_min = total * login.DELAY_SECONDS / 60

    print(f"\n{_DIV}")
    print(Color.bold("  ATTACK ANALYSIS & DEFENCE REVIEW"))
    print(f"{_DIV}\n")

    print(Color.cyan("  ── Password-Space Analysis ──────────────────────────"))
    print(f"  3-digit numeric candidates    : {total:>8,}")
    print(f"  Defender delay per attempt    : {login.DELAY_SECONDS}s")
    print(f"  Worst-case crack time         : {worst_case_min:>8.1f} minutes")
    print(f"  Expected (avg) crack time     : {worst_case_min / 2:>8.1f} minutes")

    print(f"\n{Color.cyan('  ── Defence Layers Observed ──────────────────────────')}")
    defences = [
        ("SHA-256 password hashing",            "Plaintext never stored — hashes can't be reversed"),
        ("Failed-attempt counter",              f"Persistent across sessions, resets on success"),
        (f"Rate-limiting ({login.DELAY_SECONDS}s delay)",  "Each failure costs the attacker real time"),
        (f"Lockout threshold ({login.MAX_ATTEMPTS} strikes)", "Attack window is extremely narrow"),
        ("Multi-pass secure wipe",              f"{login.WIPE_PASSES}-pass random overwrite + zero pass"),
        ("Audit log (access_log.txt)",          "Forensic trail survives file deletion"),
    ]
    for i, (name, desc) in enumerate(defences, 1):
        print(f"  {i}. {Color.bold(name)}")
        print(f"     {Color.dim(desc)}")

    print(f"\n{Color.cyan('  ── Attack Mitigations in the Real World ─────────────')}")
    mitigations = [
        "Extend password length → exponentially larger keyspace",
        "Account lockout / IP-based rate limiting",
        "Progressive back-off (2s → 4s → 8s … Jitter)",
        "CAPTCHA or proof-of-work challenge after failures",
        "Multi-Factor Authentication (MFA / TOTP)",
        "Anomaly detection & SIEM alerting on log patterns",
    ]
    for item in mitigations:
        print(f"  {Color.yellow('→')} {item}")

    print(f"\n{_DIV}\n")


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'#' * 60}")
    print(Color.bold("# GUARDIAN PRO — Brute Force Attack Simulation"))
    print(f"# {'─' * 56}")
    print("# This is a controlled educational demonstration.")
    print("# Only run this on systems you own or have permission to test.")
    print(f"{'#' * 60}\n")

    input("Press Enter to begin the simulation…\n")

    result = brute_force_attack()
    display_attack_statistics()

    outcome = Color.green("SUCCESS — Vault cracked") if result else Color.red("DEFENDED — Attacker repelled")
    print(f"[*] Simulation complete.  Outcome : {outcome}")
    print(f"[*] Full audit log written to     : '{login.LOG_FILE}'\n")
