"""
recorder.py
Captura templates de la UI del juego.

Uso:
    python recorder.py            (usa el primer device de config.json)
    python recorder.py --list     (ver qué templates faltan)
    python recorder.py --auto     (screenshot cada 3s mientras juegas)
"""

import argparse, os, time, json, sys
import cv2, numpy as np
import subprocess

CONFIG    = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))
DEVICE    = CONFIG["devices"][0]
TEMPLATES = os.path.join(os.path.dirname(__file__), "templates")

NEEDED = [
    ("title_screen",  "Pantalla de título / logo del juego"),
    ("popup_close",   "Botón X para cerrar popups"),
    ("btn_ok",        "Botón OK / Aceptar"),
    ("btn_skip",      "Botón Skip del tutorial"),
    ("dialogue_tap",  "Flecha o indicador para avanzar diálogo"),
    ("battle_screen", "Pantalla de combate"),
    ("btn_auto",      "Botón combate automático"),
    ("battle_result", "Pantalla de resultado / victoria"),
    ("btn_next",      "Botón Siguiente"),
    ("tutorial_done", "Pantalla principal (tutorial terminado)"),
]


def screenshot() -> np.ndarray | None:
    r = subprocess.run(["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=10)
    if r.returncode != 0:
        return None
    arr = np.frombuffer(r.stdout, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def list_status():
    captured = {os.path.splitext(f)[0] for f in os.listdir(TEMPLATES)} if os.path.exists(TEMPLATES) else set()
    print("\n📋 Templates\n" + "─" * 44)
    for name, desc in NEEDED:
        print(f"  {'✓' if name in captured else '✗'}  {name:<20} {desc}")
    missing = [n for n, _ in NEEDED if n not in captured]
    print(f"\n  {len(captured)}/{len(NEEDED)} capturados")
    if missing:
        print(f"  Faltan: {', '.join(missing)}\n")
    return missing


def record():
    os.makedirs(TEMPLATES, exist_ok=True)
    print(f"Conectado a {DEVICE}\n")
    print("  S → Capturar template   L → Ver estado   Q → Salir\n")
    list_status()

    while True:
        cmd = input("Comando: ").strip().lower()
        if cmd == "q":
            break
        elif cmd == "l":
            list_status()
        elif cmd == "s":
            print("Capturando...")
            screen = screenshot()
            if screen is None:
                print("❌ No se pudo capturar la pantalla")
                continue

            h, w = screen.shape[:2]
            preview = cv2.resize(screen, (int(w * 0.75), int(h * 0.75)))
            roi = cv2.selectROI("Selecciona el area - ENTER confirma, C cancela", preview, False, False)
            cv2.destroyAllWindows()

            if roi[2] == 0 or roi[3] == 0:
                print("Cancelado")
                continue

            # Escalar a resolución original
            sx, sy = w / (w * 0.75), h / (h * 0.75)
            x, y  = int(roi[0] * sx), int(roi[1] * sy)
            rw, rh = int(roi[2] * sx), int(roi[3] * sy)
            cropped = screen[y:y+rh, x:x+rw]

            cv2.imshow("Template - cualquier tecla para continuar", cropped)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

            print("\nTemplates necesarios:")
            captured = {os.path.splitext(f)[0] for f in os.listdir(TEMPLATES)}
            for i, (name, desc) in enumerate(NEEDED):
                mark = "✓" if name in captured else " "
                print(f"  [{mark}] {i+1:2d}. {name:<20} {desc}")

            choice = input("\nNúmero o nombre: ").strip()
            try:
                name = NEEDED[int(choice) - 1][0]
            except (ValueError, IndexError):
                name = choice

            if name:
                path = os.path.join(TEMPLATES, f"{name}.png")
                cv2.imwrite(path, cropped)
                print(f"✅ Guardado: {name}.png  ({rw}×{rh}px)")
                list_status()


def auto():
    out = os.path.join(os.path.dirname(__file__), "screenshots_flow")
    os.makedirs(out, exist_ok=True)
    print(f"Capturando cada 3s → {out}   (Ctrl+C para parar)\n")
    n = 0
    try:
        while True:
            s = screenshot()
            if s is not None:
                cv2.imwrite(os.path.join(out, f"frame_{n:04d}.png"), s)
                print(f"  frame_{n:04d}.png")
                n += 1
            time.sleep(3)
    except KeyboardInterrupt:
        print(f"\n✅ {n} frames guardados")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    if args.list:
        list_status()
    elif args.auto:
        auto()
    else:
        record()
