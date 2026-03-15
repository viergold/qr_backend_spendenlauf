import requests
import os
import re
import time

def get_or_set_ip(filepath="ip.ip"):
    # Regex für einfache IPv4-Prüfung
    ip_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$"

    # Falls Datei existiert, versuchen wir die IP zu lesen
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read().strip()
            if re.match(ip_regex, content):
                print(f"Gefundene IP: {content}")
                return content
            else:
                print("Keine gültige IP in der Datei gefunden.")

    # Wenn keine gültige IP vorhanden ist → Nutzer fragen
    while True:
        new_ip = input("Bitte gib eine IP-Adresse ein: ").strip()
        if re.match(ip_regex, new_ip):
            # IP speichern
            with open(filepath, "w") as f:
                f.write(new_ip)
            print(f"IP gespeichert: {new_ip}")
            return new_ip
        else:
            print("Ungültige IP. Bitte erneut eingeben.")





import rtmidi
import time

class MidiController:
    def __init__(self, port_name=None):
        self.midi_out = rtmidi.MidiOut()

        ports = self.midi_out.get_ports()
        print("Gefundene MIDI-Ports:", ports)

        # Automatisch Daslight-Port finden
        if port_name is None:
            for p in ports:
                if "daslight" in p.lower():
                    port_name = p
                    break

        port_name = "loopMIDI Port 1"
        if port_name is None:
            raise RuntimeError("Kein Daslight MIDI-Port gefunden!")

        self.midi_out.open_port(ports.index(port_name))
        print(f"Verbunden mit: {port_name}")

    # Note On
    def note_on(self, note, velocity=100, channel=0):
        status = 0x90 + channel
        self.midi_out.send_message([status, note, velocity])
        print(f"Note ON → {note}")

    # Note Off
    def note_off(self, note, channel=0):
        status = 0x80 + channel
        self.midi_out.send_message([status, note, 0])
        print(f"Note OFF → {note}")

    # Control Change (Fader/Regler)
    def cc(self, control, value, channel=0):
        status = 0xB0 + channel
        self.midi_out.send_message([status, control, value])
        print(f"CC {control} → {value}")


controller = MidiController()
locked=False
pre_run=False

off=False
last = ""
ip = "https://"+get_or_set_ip()+":5000"
print("Verwendete IP:", ip)

while True:
    try:
        response = requests.get(ip + "/status_api", verify=False)
        data = response.json()
        for key, value in data.items():
            id_lamp = int(key) + 5
            id_lamp = id_lamp * 10
            key = int(key)
            # print(key, value)
            if value == True and pre_run == False and locked == False and not last == "good":
                controller.note_on(id_lamp + 2)
                controller.note_off(id_lamp + 2)
                last = "good"
            elif value == False and pre_run == False and locked == False and not last == "bad":
                controller.note_on(id_lamp + 0)
                controller.note_off(id_lamp + 0)
                last = "bad"
            elif locked == True and pre_run == False and not last == "locked":
                controller.note_on(id_lamp + 4)
                controller.note_off(id_lamp + 4)
                last = "locked"
            elif pre_run == True and not last == "pre_run":
                controller.note_on(id_lamp + 6)
                controller.note_off(id_lamp + 6)
                last = "pre_run"


    except:
        off = True
        for i in range(6):
            i_new=i+6
            i_new = i_new * 10
            controller.note_on(i_new + 8)
            controller.note_off(i_new + 8)

    time.sleep(0.2)
    try:
        response = requests.get(ip + "/api/race_status", verify=False)
        data = response.json()
        pre_run = data["pre_run"]
        locked = not data["running"]
    except:
        off = True
        for i in range(6):
            i_new=i+6
            i_new = i_new * 10
            controller.note_on(i_new + 8)
            controller.note_off(i_new + 8)







