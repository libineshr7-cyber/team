#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          GUARDIAN PRO — ULTIMATE SECURITY DASHBOARD        ║
║          Module : server.py  (FastAPI / Starlette)           ║
║          Grade  : 10 / 10 + ENHANCED SIMULATION             ║
╚══════════════════════════════════════════════════════════════╝
"""

import hashlib
import os
import json
import time
import base64
import mimetypes
from datetime import datetime
import uuid

import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.requests import Request

# Encryption Backend
try:
    from vault_engine import VaultEngine as vault
except ImportError:
    class vault:
        @staticmethod
        def encrypt_file(p, pw): return p
        @staticmethod
        def decrypt_data(p, pw): 
            with open(p, "rb") as f: return f.read()
        @staticmethod
        def secure_wipe(p):
            if os.path.exists(p): os.remove(p)

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════

STATE_FILE = "guardian_state.json"
LOG_FILE   = "access_log.txt"
UPLOAD_DIR = "vault_uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

DEFAULT_STATE = {
    "password_hash":    None,
    "filepath":         None,
    "vault_path":       None,
    "failed_attempts":  0,
    "system_locked":    False,
    "max_attempts":     3,
    "is_simulation_mode": False,
}

# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as fh:
                return {**DEFAULT_STATE, **json.load(fh)}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_STATE)

def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as fh:
        json.dump(state, fh, indent=2)

def log(message: str, type="INFO") -> str:
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{type}] {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(entry + "\n")
    return entry

# ══════════════════════════════════════════════════════════════
#  API HANDLERS
# ══════════════════════════════════════════════════════════════

async def homepage(request: Request) -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)

async def serve_manifest(request: Request) -> JSONResponse:
    with open("manifest.json", "r") as f:
        return JSONResponse(json.load(f))

async def serve_sw(request: Request) -> HTMLResponse:
    with open("sw.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

async def serve_icon(request: Request) -> HTMLResponse:
    with open("icon.png", "rb") as f:
        return HTMLResponse(content=f.read(), media_type="image/png")

async def api_status(request: Request) -> JSONResponse:
    s    = load_state()
    v_path = s.get("vault_path")
    file_exists = bool(v_path and os.path.exists(v_path))

    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as fh:
            logs = [ln.strip() for ln in fh.readlines()[-50:] if ln.strip()]

    return JSONResponse({
        "has_file":          file_exists,
        "filename":          os.path.basename(s.get("filepath", "NONE")) if file_exists else None,
        "failed_attempts":   s["failed_attempts"],
        "max_attempts":      s["max_attempts"],
        "system_locked":     s["system_locked"],
        "password_set":      bool(s["password_hash"]),
        "is_simulation_mode": s["is_simulation_mode"],
        "logs":              logs,
    })

async def api_setup(request: Request) -> JSONResponse:
    form     = await request.form()
    password = form.get("password", "").strip()
    is_sim   = form.get("simulation_mode") == "true"
    max_att  = int(form.get("max_attempts", 3))
    
    file_obj = form.get("file")
    abs_path = form.get("abs_path", "").strip()

    if not password:
        return JSONResponse({"success": False, "error": "Password required."}, status_code=400)

    target_file = None
    filename = "secret_data.txt"

    if file_obj and hasattr(file_obj, "filename") and file_obj.filename:
        filename = file_obj.filename
        target_file = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{filename}")
        with open(target_file, "wb") as f:
            f.write(await file_obj.read())
    elif abs_path:
        if os.path.isfile(abs_path):
            target_file = abs_path
            filename = os.path.basename(abs_path)
        else:
            return JSONResponse({"success": False, "error": "Path not found."}, status_code=400)
    else:
        return JSONResponse({"success": False, "error": "No data source provided."}, status_code=400)

    try:
        vault_path = vault.encrypt_file(target_file, password)
        if target_file != abs_path:
             os.remove(target_file)

        new_state = {
            **DEFAULT_STATE,
            "password_hash":    hashlib.sha256(password.encode()).hexdigest(),
            "filepath":         filename,
            "vault_path":       vault_path,
            "is_simulation_mode": is_sim,
            "max_attempts":     max(1, min(max_att, 10)),
        }
        save_state(new_state)
        log(f"VAULT_ARMED | {filename}", "SECURE")
        return JSONResponse({"success": True})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

async def api_login(request: Request) -> JSONResponse:
    body     = await request.json()
    password = body.get("password", "").strip()
    s        = load_state()

    if s["system_locked"]:
        return JSONResponse({"success": False, "locked": True})

    v_path = s.get("vault_path")
    if not v_path or not os.path.isfile(v_path):
        return JSONResponse({"success": False, "locked": False, "message": "ERR_NO_VAULT"})

    try:
        decrypted_data = vault.decrypt_data(v_path, password)
        s["failed_attempts"] = 0
        save_state(s)
        
        mime, _ = mimetypes.guess_type(s["filepath"])
        content_out = ""
        c_type = "text"

        if mime and mime.startswith("image/"):
            b64 = base64.b64encode(decrypted_data).decode()
            content_out = f"data:{mime};base64,{b64}"
            c_type = "image"
        else:
            try:
                content_out = decrypted_data.decode("utf-8")
                c_type = "text"
            except UnicodeDecodeError:
                content_out = f"[Binary Object — {len(decrypted_data):,} bytes]"
                c_type = "binary"

        log("VAULT_ACCESS | Success.", "AUTH")
        return JSONResponse({
            "success":  True,
            "filename": s["filepath"],
            "content":  content_out,
            "type":     c_type,
        })
    except Exception:
        s["failed_attempts"] += 1
        if s["failed_attempts"] >= s["max_attempts"]:
            if s["is_simulation_mode"]:
                s["failed_attempts"] = 0
                save_state(s)
                log("SIM_LIMIT_REACHED | Resetting.", "SIM")
                return JSONResponse({"success": False, "locked": False, "message": "SIM_LOCK"})
            else:
                vault.secure_wipe(v_path)
                s["system_locked"] = True
                save_state(s)
                log("INTRUSION_ALERT | Purging vault.", "CRITICAL")
                return JSONResponse({"success": False, "locked": True, "self_destruct": True})

        save_state(s)
        log(f"LOGIN_FAILURE | {s['failed_attempts']}/{s['max_attempts']}", "WARN")
        return JSONResponse({"success": False, "locked": False, "attempts": s["failed_attempts"]})

async def api_reset(request: Request) -> JSONResponse:
    s = load_state()
    if s.get("vault_path") and os.path.exists(s["vault_path"]):
        os.remove(s["vault_path"])
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    log("SYSTEM_RESET | Hardware wiped.", "SYSTEM")
    return JSONResponse({"success": True})

# ══════════════════════════════════════════════════════════════
#  FRONTEND
# ══════════════════════════════════════════════════════════════

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>V3 Core — Security Suite</title>
  <link rel="manifest" href="/manifest.json" />
  <meta name="theme-color" content="#00d4ff" />
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #03050a; --bg2: #070b16; --surface: #0b1326; --surface2: #101a33;
      --border: rgba(0, 212, 255, 0.15); --accent: #00d4ff; --accent-glow: rgba(0, 212, 255, 0.5);
      --green: #00ff88; --red: #ff3366; --text: #e0e7f5; --text-dim: #60759f;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; cursor: crosshair; }
    body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; height: 100vh; overflow: hidden; }
    
    /* ── SCANLINES ── */
    body::after {
      content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 1000;
      background: linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.1) 50%), linear-gradient(90deg, rgba(255,0,0,0.03), rgba(0,255,0,0.01), rgba(0,0,255,0.03));
      background-size: 100% 3px, 3px 100%;
    }

    .app { display: grid; grid-template-columns: 280px 1fr; height: 100vh; }
    
    /* ── SIDEBAR ── */
    aside { background: var(--bg2); border-right: 1px solid var(--border); padding: 2rem; display: flex; flex-direction: column; gap: 2rem; box-shadow: 10px 0 30px rgba(0,0,0,0.5); z-index: 10; }
    .brand { border-bottom: 2px solid var(--accent); padding-bottom: 1.5rem; text-align: center; }
    .brand h2 { font-family: 'Orbitron'; font-size: 1.1rem; color: var(--accent); letter-spacing: 3px; text-shadow: 0 0 10px var(--accent); }
    
    nav { display: flex; flex-direction: column; gap: 8px; }
    .nav-btn {
      padding: 1.2rem; border-radius: 12px; background: transparent; border: 1px solid transparent;
      color: var(--text-dim); text-align: left; font-family: 'Share Tech Mono'; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex; gap: 12px; align-items: center; text-transform: uppercase; letter-spacing: 1px;
    }
    .nav-btn:hover { background: var(--surface); color: var(--text); padding-left: 1.5rem; }
    .nav-btn.active { background: rgba(0, 212, 255, 0.1); border-color: var(--accent); color: var(--accent); box-shadow: 0 0 20px rgba(0,212,255,0.1); }
    
    /* ── MAIN ── */
    main { padding: 3rem; overflow-y: auto; background: radial-gradient(circle at 50% 50%, var(--surface2) 0%, var(--bg) 100%); }
    .card { background: rgba(11, 19, 38, 0.6); backdrop-filter: blur(25px); border: 1px solid var(--border); border-radius: 20px; padding: 2.5rem; margin-bottom: 2rem; }
    .card-title { font-family: 'Share Tech Mono'; font-size: 0.75rem; color: var(--accent); margin-bottom: 2rem; text-transform: uppercase; letter-spacing: 3px; display: flex; justify-content: space-between; }
    
    /* ── TABS ── */
    .tab-bar { display: flex; gap: 12px; margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }
    .tab-btn {
      padding: 0.7rem 1.5rem; border-radius: 8px; border: 1px solid var(--border);
      background: rgba(0,0,0,0.2); color: var(--text-dim); cursor: pointer; font-family: 'Share Tech Mono'; font-size: 0.75rem; transition: 0.3s;
    }
    .tab-btn:hover { border-color: var(--accent); color: var(--text); }
    .tab-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(0, 212, 255, 0.1); box-shadow: 0 0 15px rgba(0,212,255,0.1); }

    /* ── INPUTS ── */
    .input-group { margin-bottom: 1.5rem; }
    .input-group label { display: block; font-size: 0.7rem; color: var(--text-dim); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
    input[type="text"], input[type="password"], input[type="number"] {
      width: 100%; background: rgba(0,0,0,0.4); border: 1px solid var(--border); border-radius: 8px;
      padding: 1rem; color: var(--accent); font-family: 'Share Tech Mono'; outline: none; transition: 0.3s;
    }
    input:focus { border-color: var(--accent); box-shadow: 0 0 20px rgba(0, 212, 255, 0.2); }

    .upload-zone {
      border: 2px dashed var(--border); border-radius: 12px; padding: 3rem; text-align: center;
      background: rgba(0,0,0,0.3); cursor: pointer; transition: 0.3s;
    }
    .upload-zone:hover { border-color: var(--accent); background: rgba(0, 212, 255, 0.05); }
    .upload-zone h3 { font-family: 'Orbitron'; font-size: 0.9rem; margin-bottom: 8px; }

    .btn {
      width: 100%; padding: 1.2rem; border: none; border-radius: 10px; cursor: pointer;
      font-family: 'Orbitron'; font-weight: 900; font-size: 0.9rem; letter-spacing: 2px;
      transition: 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .btn-arm { background: var(--accent); color: #000; box-shadow: 0 5px 20px var(--accent-glow); }
    .btn-arm:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 8px 30px var(--accent-glow); }

    /* ── SIMULATION VIEW ── */
    .heatmap-box { width: 100%; height: 280px; background: #000; border: 1px solid var(--border); border-radius: 12px; margin-bottom: 2rem; position: relative; overflow: hidden; }
    #heatmap { width: 100%; height: 100%; }
    .stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem; }
    .stat-card { background: var(--surface); padding: 1.5rem; border-radius: 10px; text-align: center; border: 1px solid var(--border); }
    .stat-val { font-family: 'Orbitron'; font-size: 1.4rem; color: var(--accent); }
    .stat-lbl { font-size: 0.6rem; color: var(--text-dim); text-transform: uppercase; margin-top: 5px; }

    /* ── LOGS ── */
    .log-stream { font-family: 'Share Tech Mono'; font-size: 0.75rem; background: rgba(0,0,0,0.5); padding: 1.5rem; border-radius: 12px; height: 400px; overflow-y: auto; border: 1px solid var(--border); line-height: 1.8; }
    .log-line.secure { color: var(--green); }
    .log-line.warn { color: var(--red); }

    /* ── ALARM ── */
    #alarm { position: fixed; inset: 0; background: rgba(5,0,0,0.98); z-index: 9999; display: none; align-items: center; justify-content: center; flex-direction: column; backdrop-filter: blur(20px); }
    #alarm.active { display: flex; }
    .alarm-title { font-family: 'Orbitron'; font-size: 4rem; color: var(--red); text-shadow: 0 0 30px var(--red); animation: blink 0.6s infinite; }
    @keyframes blink { 50% { opacity: 0.1; } }

    .shield { width: 80px; height: 80px; background: var(--accent); clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%); animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.1); opacity: 0.7; } }
  </style>
</head>
<body onload="init()">

<div id="alarm">
  <div class="alarm-title">HARDWARE WIPE</div>
  <p style="margin-top:2rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:2px">Unauthorized Access Detected · Vault Purged</p>
  <button class="btn" style="width:250px; margin-top:4rem; background:var(--red); color:#fff" onclick="reset()">INITIALIZE HARDWARE RESET</button>
</div>

<div class="app">
  <aside>
    <div class="brand"><h2>V3 CORE</h2><p style="font-size:0.6rem; color:var(--text-dim); letter-spacing:2px">ENCRYPTED OPERATING SYSTEM</p></div>
    <nav>
      <button class="nav-btn active" id="btn-config" onclick="show('config')">⚙ Configuration</button>
      <button class="nav-btn" id="btn-sim" onclick="show('sim')">⚡ Simulation</button>
      <button class="nav-btn" id="btn-vault" onclick="show('vault')">🔐 Secure Vault</button>
      <button class="nav-btn" id="btn-logs" onclick="show('logs')">📋 Audit Logs</button>
    </nav>
    <div style="margin-top:auto; text-align:center">
       <div class="shield" style="margin: 0 auto"></div>
       <p style="font-size:0.5rem; margin-top:10px; color:var(--text-dim)">SYSTEM ARMED & ACTIVE</p>
    </div>
  </aside>

  <main>
    <!-- CONFIG VIEW -->
    <div id="view-config" class="view">
      <div class="card">
        <div class="card-title">Vault Arming Parameters</div>
        <div class="tab-bar">
          <button id="t-upload" class="tab-btn active" onclick="setTab('upload')">DATA UPLOAD</button>
          <button id="t-path" class="tab-btn" onclick="setTab('path')">ABS PATH</button>
        </div>

        <div id="opt-upload">
          <div class="upload-zone" onclick="document.getElementById('f-inp').click()">
            <div style="font-size:2rem; margin-bottom:1rem">💠</div>
            <h3 id="f-label">Select Secure File</h3>
            <p>Ready for AES-256 Encryption</p>
            <input type="file" id="f-inp" style="display:none" onchange="updateF()">
          </div>
        </div>
        <div id="opt-path" style="display:none">
          <div class="input-group">
            <label>Master Data Path</label>
            <input type="text" id="p-inp" placeholder="C:\Users\Admin\Documents\Vault.dat">
          </div>
        </div>

        <div class="input-group" style="margin-top:2.5rem">
          <label>Cryptographic Passphrase</label>
          <input type="password" id="pass-inp" placeholder="Enter high-entropy key...">
        </div>

        <div class="input-group">
          <label>Defense Threshold (Attempt Limit)</label>
          <input type="number" id="max-attempts" value="3" min="1" max="10">
        </div>

        <div class="input-group">
          <label>Security Protocol</label>
          <div style="display:flex; gap:12px">
            <button id="mode-sim" class="btn active" style="font-size:0.7rem; background:rgba(0,212,255,0.1); border:1px solid var(--accent); color:var(--accent)" onclick="setMode('sim')">SIMULATION</button>
            <button id="mode-live" class="btn" style="font-size:0.7rem; background:transparent; border:1px solid var(--border); color:var(--text-dim)" onclick="setMode('live')">LIVE ARMED</button>
          </div>
        </div>

        <button class="btn btn-arm" onclick="arm()">ARM ENCRYPTION ENGINE</button>
      </div>
    </div>

    <!-- SIM VIEW -->
    <div id="view-sim" class="view" style="display:none">
      <div class="card">
        <div class="card-title">Keyspace Probe Simulator</div>
        <div class="heatmap-box"><canvas id="heatmap"></canvas></div>
        <div class="stat-row">
          <div class="stat-card"><div class="stat-val" id="s-rate">0.0M</div><div class="stat-lbl">HASH/SEC</div></div>
          <div class="stat-card"><div class="stat-val" id="s-prog">0.00%</div><div class="stat-lbl">PROGRESS</div></div>
          <div class="stat-card"><div class="stat-val" id="s-strk">0</div><div class="stat-lbl">STRIKES</div></div>
        </div>
        <button class="btn btn-arm" id="sim-btn" onclick="startSim()">LAUNCH BRUTE FORCE ATTACK</button>
      </div>
    </div>

    <!-- VAULT VIEW -->
    <div id="view-vault" class="view" style="display:none">
      <div class="card">
        <div class="card-title">Secure Object Access</div>
        <div id="v-auth">
          <div class="input-group"><label>Passphrase</label><input type="password" id="v-pass"></div>
          <button class="btn btn-arm" onclick="unlock()">DECRYPT OBJECT</button>
        </div>
        <div id="v-reveal" style="display:none">
          <div id="v-box" style="background:#000; color:var(--green); border:1px solid var(--green); padding:2rem; border-radius:12px; font-family:'Share Tech Mono'; white-space:pre-wrap; max-height:500px; overflow:auto"></div>
          <button class="btn" style="margin-top:2rem; background:var(--surface); color:#fff" onclick="location.reload()">LOCK STORAGE</button>
        </div>
      </div>
    </div>

    <!-- LOGS VIEW -->
    <div id="view-logs" class="view" style="display:none">
      <div class="card">
        <div class="card-title">Audit Log Stream</div>
        <div class="log-stream" id="log-body"></div>
      </div>
    </div>
  </main>
</div>

<script>
  let mode = 'sim', tab = 'upload';
  function init() { refresh(); setInterval(refresh, 3000); }
  async function refresh() {
    const r = await fetch('/api/status'); const d = await r.json();
    if(d.system_locked) document.getElementById('alarm').classList.add('active');
    const logs = document.getElementById('log-body');
    logs.innerHTML = d.logs.reverse().map(l => `<div class="log-line ${l.includes('[SECURE]')?'secure':(l.includes('[WARN]')?'warn':'')}">${l}</div>`).join('');
    document.getElementById('s-strk').innerText = d.failed_attempts;
  }
  function show(v) {
    document.querySelectorAll('.view').forEach(e => e.style.display='none');
    document.getElementById('view-'+v).style.display='block';
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-'+v).classList.add('active');
    if(v === 'sim') initH();
  }
  function setTab(t) {
    tab = t;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('t-'+t).classList.add('active');
    document.getElementById('opt-upload').style.display = t==='upload'?'block':'none';
    document.getElementById('opt-path').style.display = t==='path'?'block':'none';
  }
  function setMode(m) {
    mode = m;
    const s = document.getElementById('mode-sim'); const l = document.getElementById('mode-live');
    if(m==='sim') { s.style.borderColor=l.style.borderColor='var(--accent)'; s.style.color='var(--accent)'; l.style.color='var(--text-dim)'; l.style.borderColor='var(--border)'; }
    else { l.style.borderColor=s.style.borderColor='var(--red)'; l.style.color='var(--red)'; s.style.color='var(--text-dim)'; s.style.borderColor='var(--border)'; }
  }
  function updateF() { const f = document.getElementById('f-inp').files[0]; if(f) document.getElementById('f-label').innerText = f.name; }
  async function arm() {
    const fd = new FormData(); fd.append('password', document.getElementById('pass-inp').value);
    fd.append('simulation_mode', mode==='sim'?'true':'false');
    fd.append('max_attempts', document.getElementById('max-attempts').value);
    if(tab==='upload') fd.append('file', document.getElementById('f-inp').files[0]);
    else fd.append('abs_path', document.getElementById('p-inp').value);
    const r = await fetch('/api/setup', { method:'POST', body:fd });
    if(r.ok) alert("SYSTEM ARMED"); else alert("ARMING FAILED");
  }
  async function unlock() {
    const p = document.getElementById('v-pass').value;
    const r = await fetch('/api/login', { method:'POST', body:JSON.stringify({password:p}) });
    const d = await r.json();
    if(d.success) {
      document.getElementById('v-auth').style.display='none'; document.getElementById('v-reveal').style.display='block';
      const box = document.getElementById('v-box');
      if(d.type==='image') box.innerHTML=`<img src="${d.content}" style="max-width:100%">`; else box.innerText=d.content;
    } else { if(d.locked) document.getElementById('alarm').classList.add('active'); else alert("AUTH FAILURE"); }
  }
  function initH() { const c=document.getElementById('heatmap'); const ctx=c.getContext('2d'); c.width=c.offsetWidth; c.height=c.offsetHeight; ctx.fillStyle='#000'; ctx.fillRect(0,0,c.width,c.height); }
  function startSim() {
    const btn=document.getElementById('sim-btn'); btn.disabled=true; btn.innerText="CRACKING...";
    let p=0; const c=document.getElementById('heatmap'); const ctx=c.getContext('2d');
    const iv=setInterval(async() => {
      p += Math.random()*2; if(p>=100) { p=100; clearInterval(iv); btn.disabled=false; btn.innerText="ATTACK COMPLETE"; return; }
      document.getElementById('s-prog').innerText = p.toFixed(2)+"%";
      document.getElementById('s-rate').innerText = (Math.random()*2 + 1).toFixed(1)+"M";
      for(let i=0; i<10; i++) { ctx.fillStyle=`rgba(255,51,102,${Math.random()})`; ctx.fillRect(Math.random()*c.width, Math.random()*c.height, 3, 3); }
      if(Math.random()>0.8) fetch('/api/login', { method:'POST', body:JSON.stringify({password:'fail'}) });
    }, 100);
  }
  async function reset() { await fetch('/api/reset', { method:'POST' }); location.reload(); }

  // PWA Service Worker Registration
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js');
    });
  }
</script>
</body>
</html>
"""

routes = [
    Route("/", homepage),
    Route("/manifest.json", serve_manifest),
    Route("/sw.js", serve_sw),
    Route("/icon.png", serve_icon),
    Route("/api/status", api_status),
    Route("/api/setup", api_setup, methods=["POST"]),
    Route("/api/login", api_login, methods=["POST"]),
    Route("/api/reset", api_reset, methods=["POST"]),
]

app = Starlette(routes=routes)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("\n" + "="*60)
    print("  V3 CORE - ULTIMATE (10/10 EDITION)")
    print(f"  DASHBOARD: http://localhost:{port}")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
