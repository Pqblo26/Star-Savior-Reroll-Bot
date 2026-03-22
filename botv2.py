"""
bot.py - Star Savior Tutorial Bot
"""

import subprocess, time, threading, json, os
import cv2, numpy as np

# ── Config ─────────────────────────────────────────────────────────────────────

CONFIG           = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))
DEVICES          = CONFIG["devices"]
STEP_DELAY       = CONFIG.get("step_delay", 0.5)
POLL_DELAY       = CONFIG.get("poll_delay", 0.8)
TIMEOUT          = CONFIG.get("tutorial_timeout", 600)
PLAYER_NAME      = CONFIG.get("player_name", "Shiro")
START_STEP       = CONFIG.get("start_step", 1)
TEMPLATES        = os.path.join(os.path.dirname(__file__), "templates")
SKILL_ATTACK_WAIT = 10.0

GACHA_TARGETS = {"asherah": 2, "emily": 1, "charlotte": 1, "lacy": 1}

# ── Sequence ───────────────────────────────────────────────────────────────────

SEQUENCE = [
    ("habilidad1",            "skill"),
    ("habilidad2",            "skill"),
    ("habilidad3",            "skill"),
    ("habilidad4",            "skill"),
    ("habilidad5_tocar",      "tap"),
    ("habilidad6",            "skill"),
    ("habilidad7",            "skill"),
    ("habilidad8",            "skill"),
    ("nombre",                "enter_name"),
    ("observation",           "tap_when_arrow"),
    ("pull_tutorial",         "tap_when_arrow"),
    ("confirm_blanco",        "tap"),
    ("volver_menu",           "tap"),
    ("mainstream",            "tap_when_arrow"),
    ("journey",               "tap_when_arrow"),
    ("start",                 "tap_when_arrow"),
    ("select",                "tap_when_arrow"),
    ("mas_personaje",         "tap_when_arrow"),
    ("equipar_personaje",     "tap_when_arrow"),
    ("auto_equip",            "tap_when_arrow"),
    ("lupa",                  "tap_when_arrow"),
    ("cancel_x",              "tap_when_arrow"),
    ("auto_formation",        "tap_when_arrow"),
    ("beginning_journey",     "tap_when_arrow"),
    ("skip_tutorial",         "tap"),
    ("training",              "tap_slow"),
    ("empezar_training",      "tap"),
    ("rest",                  "tap_slow"),
    ("empezar_rest",          "tap_only"),
    ("training",              "tap_slow"),
    ("empezar_training",      "tap"),
    ("trial",                 "tap_slow"),
    ("accept",                "tap_only"),
    ("star_quest",            "tap"),
    ("auto_battle",           "tap_delayed_check"),
    ("leave",                 "tap"),
    ("journey_end",           "tap"),
    ("confirm_paso39",        "tap"),
    ("cancel_x_paso40",       "tap_slow"),
    ("3_tickets_uno",         "tap"),
    ("recoger_tickets_1",     "tap"),
    ("3_tickets_dos",         "tap"),
    ("recoger_tickets_2",     "tap"),
    ("cancel_x_paso45",       "tap_slow"),
    ("manage",                "tap_when_arrow"),
    ("savior",                "tap"),
    ("view_details",          "tap_when_arrow"),
    ("gear",                  "tap_when_arrow"),
    ("mas_colocar_personaje", "tap_when_arrow"),
    ("equip",                 "tap_when_arrow"),
    ("volver_menu",           "tap"),
    ("skip_tutorial",         "tap"),
    ("skip_tutorial",         "tap"),
    ("libro_rojo",            "tap"),
    ("challenges",            "tap"),
    ("claim_all",             "tap"),
    ("cancel_x_paso58",       "tap_slow"),
    ("observation_tirar",     "tap"),
    ("banner1",               "tap"),
    ("10_pulls",              "gacha"),
    ("confirm_blanco_paso62", "tap"),
    ("_scroll",               "scroll_only"),
    ("banner2",               "tap"),
    ("single_pull_uno",       "single_gacha"),
    ("confirm_blanco_paso68", "tap"),
    ("inicio",                "tap"),
    ("ajustes",               "tap"),
    ("account",               "tap"),
    ("log_out",               "tap"),
    ("guest_login",           "tap"),
]

ALWAYS = [
    ("arcana_event", "tap_3x"),
    ("skip_story",   "skip_story"),
    ("skip_journey", "tap"),
    ("confirm",      "tap"),
]

NO_TEMPLATE_ACTIONS = ("scroll_only",)

stop_event    = threading.Event()
device_totals = {}
device_steps  = {}

STATE_FILE = os.path.join(os.path.dirname(__file__), "estado.json")

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(device_steps, f)
    print("Estado guardado en estado.json")

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)

# ── ADB helpers ────────────────────────────────────────────────────────────────

def adb(device, *args):
    subprocess.run(["adb", "-s", device] + list(args), capture_output=True, timeout=10)

def adb_screenshot(device):
    r = subprocess.run(["adb", "-s", device, "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=10)
    if r.returncode != 0:
        return None
    arr = np.frombuffer(r.stdout, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def adb_tap(device, x, y):
    adb(device, "shell", "input", "tap", str(x), str(y))
    time.sleep(STEP_DELAY)

def adb_type(device, text):
    adb(device, "shell", "input", "text", text)
    time.sleep(0.3)

def adb_enter(device):
    adb(device, "shell", "input", "keyevent", "KEYCODE_ENTER")
    time.sleep(0.3)

# ── Template matching ──────────────────────────────────────────────────────────

_cache = {}

def find(screen, name, threshold=0.75):
    if name not in _cache:
        path = os.path.join(TEMPLATES, name + ".png")
        if not os.path.exists(path):
            return None
        _cache[name] = cv2.imread(path)
    tmpl = _cache[name]
    if tmpl is None or screen is None:
        return None
    s = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    t = cv2.cvtColor(tmpl,   cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, val, _, loc = cv2.minMaxLoc(res)
    if val >= threshold:
        h, w = t.shape[:2]
        return loc[0] + w // 2, loc[1] + h // 2, val
    return None

def wait_for(device, name, timeout=8, threshold=0.75):
    start = time.time()
    while time.time() - start < timeout and not stop_event.is_set():
        screen = adb_screenshot(device)
        if screen is not None:
            m = find(screen, name, threshold=threshold)
            if m:
                return m
        time.sleep(0.5)
    return None

def count_template(screen, name, threshold=0.75):
    if name not in _cache:
        path = os.path.join(TEMPLATES, name + ".png")
        if not os.path.exists(path):
            return 0
        _cache[name] = cv2.imread(path)
    tmpl = _cache[name]
    if tmpl is None or screen is None:
        return 0
    s = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    t = cv2.cvtColor(tmpl,   cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    locations = np.where(res >= threshold)
    if len(locations[0]) == 0:
        return 0
    points = list(zip(locations[1], locations[0]))
    kept = []
    for p in sorted(points, key=lambda x: res[x[1], x[0]], reverse=True):
        if all(abs(p[0]-k[0]) > 30 or abs(p[1]-k[1]) > 30 for k in kept):
            kept.append(p)
    return len(kept)

def check_objectives(device, totals):
    ash = totals.get("asherah", 0)
    emi = totals.get("emily", 0)
    cha = totals.get("charlotte", 0)
    lac = totals.get("lacy", 0)
    rules = [
        ash >= 2 and emi >= 1 and cha >= 1,
        ash >= 3 and emi >= 1,
        ash >= 3 and cha >= 1,
        ash >= 3 and lac >= 1,
        ash >= 2 and lac >= 1 and emi >= 1,
        ash >= 2 and lac >= 1 and cha >= 1,
        ash >= 4,
    ]
    if any(rules):
        print("[" + device + "] Objetivo conseguido " + str(totals) + ", parando instancia")
        return True
    return False

# ── Actions ────────────────────────────────────────────────────────────────────

def do_skill(device, cx, cy, skill_name):
    screen = adb_screenshot(device)
    if not find(screen, "tutorial_indicator"):
        h, w = screen.shape[:2]
        adb_tap(device, w // 2, int(h * 0.8))
        return False
    adb_tap(device, cx, cy)
    deadline = time.time() + SKILL_ATTACK_WAIT
    while time.time() < deadline and not stop_event.is_set():
        screen2 = adb_screenshot(device)
        if screen2 is not None:
            if skill_name == "habilidad8":
                circle = find(screen2, "circulo_habilidad8", threshold=0.70)
            else:
                circle = find(screen2, "circulo_rojo_ataque", threshold=0.70)
                if not circle:
                    circle = find(screen2, "circulo_rojo_ataque2", threshold=0.70)
                if not circle:
                    circle = find(screen2, "circulo_rojo_ataque3", threshold=0.70)
            if circle:
                cx2, cy2, _ = circle
                print("[" + device + "] Circulo detectado, tapando (" + str(cx2) + "," + str(cy2) + ")")
                adb_tap(device, cx2, cy2)
                return True
            h, w = screen2.shape[:2]
            adb_tap(device, w // 2, int(h * 0.8))
        time.sleep(0.3)
    return True

def do_tap_when_arrow(device, cx, cy):
    deadline = time.time() + 3.0
    while time.time() < deadline and not stop_event.is_set():
        screen = adb_screenshot(device)
        if screen is not None:
            h, w = screen.shape[:2]
            adb_tap(device, w // 2, int(h * 0.8))
        time.sleep(0.5)
    screen = adb_screenshot(device)
    if screen is not None and find(screen, "tutorial_indicator"):
        adb_tap(device, cx, cy)
        return True
    if screen is not None:
        h, w = screen.shape[:2]
        adb_tap(device, w // 2, int(h * 0.8))
    return False

def do_tap_slow(device, cx, cy):
    deadline = time.time() + 3.0
    while time.time() < deadline and not stop_event.is_set():
        s = adb_screenshot(device)
        h, w = s.shape[:2] if s is not None else (540, 960)
        adb_tap(device, w // 2, int(h * 0.8))
        time.sleep(0.8)
    adb_tap(device, cx, cy)
    return True

def do_tap_delayed_check(device, cx, cy):
    print("[" + device + "] Esperando 15s antes de tapear auto_battle...")
    deadline = time.time() + 15.0
    while time.time() < deadline and not stop_event.is_set():
        s = adb_screenshot(device)
        h, w = s.shape[:2] if s is not None else (540, 960)
        adb_tap(device, w // 2, int(h * 0.8))
        time.sleep(1.0)
    adb_tap(device, cx, cy)
    for attempt in range(3):
        time.sleep(1.0)
        screen = adb_screenshot(device)
        if screen is None:
            break
        m = find(screen, "auto_battle")
        if not m:
            print("[" + device + "] auto_battle no visible, asumiendo activado")
            break
        cx_m, cy_m, _ = m
        x1, y1 = max(0, cx_m - 10), max(0, cy_m - 10)
        region = screen[y1:y1+20, x1:x1+20]
        brightness = float(cv2.cvtColor(region, cv2.COLOR_BGR2GRAY).mean())
        print("[" + device + "] auto_battle brillo=" + str(round(brightness, 1)))
        if brightness > 95:
            print("[" + device + "] auto_battle activado")
            break
        print("[" + device + "] auto_battle no activado, reintentando...")
        adb_tap(device, cx_m, cy_m)
    return True

def do_tap_3x(device, cx, cy):
    for _ in range(5):
        adb_tap(device, cx, cy)
        time.sleep(0.3)

def do_skip_story(device, cx, cy):
    adb_tap(device, cx, cy)
    m = wait_for(device, "confirm", timeout=5)
    if m:
        adb_tap(device, m[0], m[1])

def do_enter_name(device, cx, cy):
    adb_tap(device, cx, cy)
    time.sleep(0.3)
    adb_type(device, PLAYER_NAME)
    adb_enter(device)
    m = wait_for(device, "confirm", timeout=5)
    if m:
        adb_tap(device, m[0], m[1])

def do_scroll_only(device, cx, cy):
    adb(device, "shell", "input", "touchscreen", "swipe", "100", "400", "100", "100", "1500")
    time.sleep(2.0)
    return True

def _handle_pull_result(device, totals, wait=8):
    """Durante `wait` segundos pulsa skip_story y confirm en cuanto aparecen. Luego cuenta SSRs."""
    deadline = time.time() + wait
    while time.time() < deadline and not stop_event.is_set():
        screen = adb_screenshot(device)
        if screen is None:
            time.sleep(0.3)
            continue
        m = find(screen, "skip_story", threshold=0.60)
        if m:
            adb_tap(device, m[0], m[1])
            continue
        m = find(screen, "confirm")
        if m:
            adb_tap(device, m[0], m[1])
            continue
        time.sleep(0.3)

    screen = adb_screenshot(device)
    if screen is not None:
        for ssr in GACHA_TARGETS:
            count = count_template(screen, ssr)
            totals[ssr] += count
            print("[" + device + "] " + ssr + ": +" + str(count) + " | total: " + str(totals[ssr]) + "/" + str(GACHA_TARGETS[ssr]))

    if check_objectives(device, totals):
        return "stop"
    return "continue"

def do_gacha(device, cx, cy):
    totals = {ssr: 0 for ssr in GACHA_TARGETS}

    for pull in range(5):
        print("[" + device + "] Multi " + str(pull+1) + "/5")
        if pull == 0:
            adb_tap(device, cx, cy)
        else:
            m = wait_for(device, "10_pulls_otra", timeout=15)
            if m:
                adb_tap(device, m[0], m[1])
            else:
                print("[" + device + "] No se encontro 10_pulls_otra, parando")
                break

        result = _handle_pull_result(device, totals, wait=12)
        if result == "stop":
            return "stop"

    print("[" + device + "] Sin objetivo tras 5 multis, continuando con singles...")
    device_totals[device] = totals
    return True

def do_single_gacha(device, cx, cy):
    totals = device_totals.get(device, {ssr: 0 for ssr in GACHA_TARGETS})

    for i in range(6):
        print("[" + device + "] Single " + str(i+1) + "/6")
        if i == 0:
            time.sleep(1.5)
            adb_tap(device, cx, cy)
        else:
            m = wait_for(device, "single_pull_dos", timeout=15)
            if m:
                adb_tap(device, m[0], m[1])
            else:
                print("[" + device + "] No se encontro single_pull_dos")
                break

        result = _handle_pull_result(device, totals, wait=8)
        if result == "stop":
            return "stop"

    print("[" + device + "] Sin objetivo tras singles, continuando con reroll")
    device_steps[device] = 0
    return True

# ── Execute ────────────────────────────────────────────────────────────────────

def execute(device, action, cx, cy, template_name=""):
    if action == "tap":
        adb_tap(device, cx, cy)
        return True
    elif action == "tap_slow":
        return do_tap_slow(device, cx, cy)
    elif action == "tap_only":
        adb_tap(device, cx, cy)
        return True
    elif action == "tap_when_arrow":
        return do_tap_when_arrow(device, cx, cy)
    elif action == "tap_delayed_check":
        return do_tap_delayed_check(device, cx, cy)
    elif action == "tap_3x":
        do_tap_3x(device, cx, cy)
        return True
    elif action == "skill":
        return do_skill(device, cx, cy, template_name)
    elif action == "enter_name":
        do_enter_name(device, cx, cy)
        return True
    elif action == "skip_story":
        do_skip_story(device, cx, cy)
        return True
    elif action == "gacha":
        return do_gacha(device, cx, cy)
    elif action == "single_gacha":
        return do_single_gacha(device, cx, cy)
    elif action == "scroll_only":
        return do_scroll_only(device, cx, cy)
    return True

# ── Main loop ──────────────────────────────────────────────────────────────────

def run_tutorial(device):
    attempt = 0
    saved = load_state()
    if device in saved and saved[device] > 0:
        print("[" + device + "] Retomando desde paso " + str(saved[device]+1) + " (estado guardado)")
        device_steps[device] = saved[device]
    while not stop_event.is_set():
        attempt += 1
        print("[" + device + "] Intento " + str(attempt))
        result = _run_attempt(device)
        if result == "stop":
            print("[" + device + "] Cuenta guardada. Pulsa Enter para reiniciar esta instancia...")
            input()
            print("[" + device + "] Reiniciando...")

def _run_attempt(device):
    step  = device_steps.get(device, max(0, START_STEP - 1))
    total = len(SEQUENCE)
    start = time.time()

    while time.time() - start < TIMEOUT and not stop_event.is_set():
        screen = adb_screenshot(device)
        if screen is None:
            print("[" + device + "] Sin pantalla, reintentando...")
            time.sleep(2)
            continue

        current_template, current_action = SEQUENCE[step]
        device_steps[device] = step

        # ── ALWAYS ──
        always_handled = False
        if current_action != "tap_only":
            for template, action in ALWAYS:
                t = 0.60 if template in ("skip_story", "skip_journey") else 0.75
                m = find(screen, template, threshold=t)
                if m:
                    if template == "skip_journey":
                        if step >= 39:
                            continue
                        cx_m, cy_m, _ = m
                        x1, y1 = max(0, cx_m - 10), max(0, cy_m - 10)
                        region = screen[y1:y1+20, x1:x1+20]
                        brightness = float(cv2.cvtColor(region, cv2.COLOR_BGR2GRAY).mean())
                        print("[" + device + "] skip_journey brillo=" + str(round(brightness, 1)))
                        if brightness < 75:
                            print("[" + device + "] skip_journey sin brillo, ignorando")
                            continue
                    cx, cy, conf = m
                    print("[" + device + "] [ALWAYS] " + template + " (" + str(round(conf, 2)) + ")")
                    execute(device, action, cx, cy)
                    always_handled = True
                    break

        if always_handled:
            time.sleep(POLL_DELAY)
            continue

        # ── Acciones sin template ──
        if current_action in NO_TEMPLATE_ACTIONS:
            print("[" + device + "] [" + str(step+1) + "/" + str(total) + "] " + current_action)
            acted = execute(device, current_action, 0, 0)
            if acted == "stop":
                return "stop"
            step += 1
            if step >= total:
                print("[" + device + "] Secuencia completada, reiniciando reroll...")
                return
            time.sleep(POLL_DELAY)
            continue

        # ── Paso normal ──
        m = find(screen, current_template)
        if m:
            cx, cy, conf = m
            print("[" + device + "] [" + str(step+1) + "/" + str(total) + "] " + current_template + " (" + str(round(conf, 2)) + ")")

            if current_action == "done":
                print("[" + device + "] Tutorial completado!")
                return

            acted = execute(device, current_action, cx, cy, current_template)
            if acted == "stop":
                print("[" + device + "] Instancia detenida por objetivo conseguido")
                return "stop"
            elif acted:
                step += 1
                if step >= total:
                    print("[" + device + "] Secuencia completada, reiniciando reroll...")
                    return
        else:
            if current_action == "tap_only":
                print("[" + device + "] Esperando sin tocar... (paso " + str(step+1) + ": " + current_template + ")")
            else:
                h, w = screen.shape[:2]
                adb_tap(device, w // 2, int(h * 0.8))
                print("[" + device + "] Avanzando dialogo... (esperando paso " + str(step+1) + ": " + current_template + ")")

        time.sleep(POLL_DELAY)

    if not stop_event.is_set():
        print("[" + device + "] Timeout tras " + str(TIMEOUT) + "s, reiniciando...")

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DEVICES:
        print("No hay devices en config.json")
        raise SystemExit(1)

    print("Instancias: " + str(DEVICES))
    print("Nombre:     " + PLAYER_NAME)
    print("Pasos:      " + str(len(SEQUENCE)))
    print("Desde paso: " + str(START_STEP) + "\n")
    print("Ctrl+C para parar\n")

    threads = [threading.Thread(target=run_tutorial, args=(d,), daemon=True) for d in DEVICES]
    for t in threads:
        t.start()

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nParando bot...")
        stop_event.set()
        for t in threads:
            t.join(timeout=5)
        save_state()
        print("Bot detenido.")
