import os
import re
import time
import requests
import rtmidi


# ---------------------------------------------------------
# IP HANDLING
# ---------------------------------------------------------

def get_or_set_ip(filepath="ip.ip"):
    """Liest eine gespeicherte IP oder fragt den Nutzer nach einer neuen."""
    ip_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$"

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read().strip()
            if re.match(ip_regex, content):
                print(f"Gefundene IP: {content}")
                return content
            print("Keine gültige IP in der Datei gefunden.")

    while True:
        new_ip = input("Bitte gib eine IP-Adresse ein: ").strip()
        if re.match(ip_regex, new_ip):
            with open(filepath, "w") as f:
                f.write(new_ip)
            print(f"IP gespeichert: {new_ip}")
            return new_ip
        print("Ungültige IP. Bitte erneut eingeben.")


# ---------------------------------------------------------
# MIDI CONTROLLER
# ---------------------------------------------------------

class MidiController:
    def __init__(self, port_name=None):
        self.midi_out = rtmidi.MidiOut()
        ports = self.midi_out.get_ports()

        print("Gefundene MIDI-Ports:", ports)

        # Automatische Port-Suche
        if port_name is None:
            for p in ports:
                if "daslight" in p.lower() or "loopmidi" in p.lower():
                    port_name = p
                    break

        if port_name is None:
            raise RuntimeError("Kein passender MIDI-Port gefunden!")

        self.midi_out.open_port(ports.index(port_name))
        print(f"Verbunden mit: {port_name}")

    def note_on(self, note, velocity=100, channel=0):
        self.midi_out.send_message([0x90 + channel, note, velocity])
        print(f"Note ON → {note}")

    def note_off(self, note, channel=0):
        self.midi_out.send_message([0x80 + channel, note, 0])
        print(f"Note OFF → {note}")

    def cc(self, control, value, channel=0):
        self.midi_out.send_message([0xB0 + channel, control, value])
        print(f"CC {control} → {value}")


# ---------------------------------------------------------
# KONSTANTEN
# ---------------------------------------------------------

BASE_NOTES = {1: 60, 2: 70, 3: 80, 4: 90}

OFFSETS = {
    "inactive": 0,
    "active": 2,
    "scanner": 4,
    "off": 6
}


# ---------------------------------------------------------
# HILFSFUNKTIONEN
# ---------------------------------------------------------

def safe_get_json(url):
    """Sicheres GET mit JSON-Parsing."""
    try:
        r = requests.get(url, verify=False, timeout=1.5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠️ Fehler bei Request {url}: {e}")
        return None


def black(controller):
    """Alle Scanner auf OFF setzen."""
    for i in range(1, 5):
        note = BASE_NOTES[i] + OFFSETS["off"]
        controller.note_on(note)
        controller.note_off(note)


# ---------------------------------------------------------
# HAUPTPROGRAMM
# ---------------------------------------------------------

controller = MidiController()
ip = "https://" + get_or_set_ip() + ":5000"
print("Verwendete IP:", ip)

last_race_state = None
last_scanner_state = {i: None for i in range(1, 5)}

while True:
    # Rennstatus
    data = safe_get_json(ip + "/api/race_status")
    if not data:
        time.sleep(0.5)
        continue

    # Scannerstatus (1–6)
    data2 = safe_get_json(ip + "/status_api")
    if not data2:
        time.sleep(0.5)
        continue

    print(data)
    print(data2)

    running = data["running"]
    pre_run = data["pre_run"]
    test_run = data["test_run"]

    # Zustand vorher merken
    prev_running = last_race_state == "running"
    prev_pre = last_race_state == "pre_run"
    prev_test = last_race_state == "test_run"

    # -----------------------------------------------------
    # RENNSTATUS
    # -----------------------------------------------------

    # TEST RUN
    if test_run and last_race_state != "test_run":
        controller.note_on(52)
        controller.note_off(52)
        black(controller)
        last_race_state = "test_run"

    # PRE RUN
    elif pre_run and last_race_state != "pre_run":
        controller.note_on(50)
        controller.note_off(50)
        black(controller)
        last_race_state = "pre_run"

    # RUNNING
    elif running and last_race_state != "running":
        controller.note_on(54)
        controller.note_off(54)
        last_race_state = "running"

    # STOPPED
    elif not running and not pre_run and not test_run:

        # 🔥 Wenn ein aktiver Modus deaktiviert wurde → Signal 54 senden
        if prev_running or prev_pre or prev_test:
            controller.note_on(54)
            controller.note_off(54)

        # Normales Stop-Signal
        if last_race_state != "stopped":
            controller.note_on(53)
            controller.note_off(53)

        # Scanner zurücksetzen
        for i in last_scanner_state:
            last_scanner_state[i] = None

        black(controller)
        last_race_state = "stopped"

    # -----------------------------------------------------
    # SCANNER STATUS
    # -----------------------------------------------------
    if running:
        for i in range(1, 5):
            scan_data = safe_get_json(f"{ip}/api/scan_status/{i}")
            if not scan_data:
                continue

            new_state = (
                "scanner" if scan_data["scanner"]
                else "active" if data2.get(str(i))
                else "inactive"
            )

            if new_state != last_scanner_state[i]:
                note = BASE_NOTES[i] + OFFSETS[new_state]
                controller.note_on(note)
                controller.note_off(note)
                last_scanner_state[i] = new_state

    time.sleep(0.3)