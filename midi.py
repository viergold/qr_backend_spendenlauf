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

# Button drücken
controller.note_on(54)
controller.note_off(54)

