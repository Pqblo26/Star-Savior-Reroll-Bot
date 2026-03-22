"""
debug_template.py
Muestra en qué parte de la pantalla detecta un template y con qué confianza.
Guarda un screenshot con el match marcado en debug_output/

Uso:
    python debug_template.py circulo_rojo_ataque
    python debug_template.py habilidad1
"""

import sys, os, subprocess
import cv2, numpy as np
import json

CONFIG    = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))
DEVICE    = CONFIG["devices"][0]
TEMPLATES = os.path.join(os.path.dirname(__file__), "templates")
OUT_DIR   = os.path.join(os.path.dirname(__file__), "debug_output")

def screenshot():
    r = subprocess.run(
        ["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
        capture_output=True, timeout=10
    )
    arr = np.frombuffer(r.stdout, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def debug(name):
    os.makedirs(OUT_DIR, exist_ok=True)

    tmpl_path = os.path.join(TEMPLATES, f"{name}.png")
    if not os.path.exists(tmpl_path):
        print(f"Template no encontrado: {tmpl_path}")
        return

    print(f"Capturando pantalla de {DEVICE}...")
    screen = screenshot()
    if screen is None:
        print("No se pudo capturar la pantalla")
        return

    tmpl = cv2.imread(tmpl_path)
    s = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    t = cv2.cvtColor(tmpl,   cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, val, _, loc = cv2.minMaxLoc(res)

    th, tw = t.shape[:2]
    cx = loc[0] + tw // 2
    cy = loc[1] + th // 2

    print(f"Mejor match: confianza={val:.3f} en ({cx}, {cy})")
    print(f">>> CONFIANZA: {val:.3f} <<<")
    # Medir brillo en la zona del match
    x1, y1 = max(0, cx - 10), max(0, cy - 10)
    region = screen[y1:y1+20, x1:x1+20]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    print(f">>> BRILLO: {brightness:.1f} <<<")
    print(f"Threshold actual: 0.80")
    print(f"{'DETECTADO' if val >= 0.80 else 'NO detectado (por debajo del threshold)'}")

    # Dibujar rectángulo en el match
    debug_img = screen.copy()
    cv2.rectangle(debug_img, loc, (loc[0]+tw, loc[1]+th), (0, 0, 255), 3)
    cv2.putText(debug_img, f"{name} {val:.3f}", (loc[0], loc[1]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    out_path = os.path.join(OUT_DIR, f"debug_{name}.png")
    cv2.imwrite(out_path, debug_img)
    print(f"\nScreenshot guardado en: {out_path}")
    print("Abre esa imagen para ver dónde está detectando el bot el template.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python debug_template.py <nombre_template>")
        print("Ejemplo: python debug_template.py circulo_rojo_ataque")
        sys.exit(1)
    debug(sys.argv[1])
