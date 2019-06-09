#!/usr/bin/python3

import os.path
import glob
import re
import mido
import mido.backends.rtmidi
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from functools import reduce

SYSEX_ID = 0x7d

SYSEX_COMMANDS = {
    'set_midi_channel':     0,
    'set_midi_message':     1,
    'set_control_number':   2,
    'set_input_gain':       3,
    'set_curve':            4,
    'save_to_eeprom':       5,
}

MIDI_MESSAGES = {
    'control_change':       'Control Change',
    'channel_pressure':     'Channel Pressure (Aftertouch)',
    'pitch_bend_up':        'Pitch Bend Up',
    'pitch_bend_down':      'Pitch Bend Down',
}

CONTROL_NUMBERS = [
    '0 (Bank Select)',
    '1 (Modulation)',
    '2 (Breath Controller)',
    '3',
    '4 (Foot Controller)',
    '5 (Portamento Time)',
    '6 (Data Entry MSB)',
    '7 (Volume)',
    '8 (Balance)',
    '9',
    '10 (Pan)',
    '11 (Expression)',
    '12 (Effect Control 1)',
    '13 (Effect Control 2)',
    '14',
    '15',
    '16 (General Purpose 1)',
    '17 (General Purpose 2)',
    '18 (General Purpose 3)',
    '19 (General Purpose 4)',
    '20',
    '21',
    '22',
    '23',
    '24',
    '25',
    '26',
    '27',
    '28',
    '29',
    '30',
    '31',
    '32 (LSB for Control 0)',
    '33 (LSB for Control 1)',
    '34 (LSB for Control 2)',
    '35 (LSB for Control 3)',
    '36 (LSB for Control 4)',
    '37 (LSB for Control 5)',
    '38 (LSB for Control 6)',
    '39 (LSB for Control 7)',
    '40 (LSB for Control 8)',
    '41 (LSB for Control 9)',
    '42 (LSB for Control 10)',
    '43 (LSB for Control 11)',
    '44 (LSB for Control 12)',
    '45 (LSB for Control 13)',
    '46 (LSB for Control 14)',
    '47 (LSB for Control 15)',
    '48 (LSB for Control 16)',
    '49 (LSB for Control 17)',
    '50 (LSB for Control 18)',
    '51 (LSB for Control 19)',
    '52 (LSB for Control 20)',
    '53 (LSB for Control 21)',
    '54 (LSB for Control 22)',
    '55 (LSB for Control 23)',
    '56 (LSB for Control 24)',
    '57 (LSB for Control 25)',
    '58 (LSB for Control 26)',
    '59 (LSB for Control 27)',
    '60 (LSB for Control 28)',
    '61 (LSB for Control 29)',
    '62 (LSB for Control 30)',
    '63 (LSB for Control 31)',
    '64 (Damper Pedal)',
    '65 (Portamento on/off)',
    '66 (Sostenuto Pedal)',
    '67 (Soft Pedal)',
    '68 (Legato Footswitch)',
    '69 (Hold 2)',
    '70 (Sound Controller 1)',
    '71 (Sound Controller 2)',
    '72 (Sound Controller 3)',
    '73 (Sound Controller 4)',
    '74 (Sound Controller 5)',
    '75 (Sound Controller 6)',
    '76 (Sound Controller 7)',
    '77 (Sound Controller 8)',
    '78 (Sound Controller 9)',
    '79 (Sound Controller 10)',
    '80 (General Purpose 5)',
    '81 (General Purpose 6)',
    '82 (General Purpose 7)',
    '83 (General Purpose 8)',
    '84 (Portamento Control)',
    '85',
    '86',
    '87',
    '88',
    '89',
    '90',
    '91 (Effect 1 Depth)',
    '92 (Effect 2 Depth)',
    '93 (Effect 3 Depth)',
    '94 (Effect 4 Depth)',
    '95 (Effect 5 Depth)',
    '96 (Data Increment)',
    '97 (Data Decrement)',
    '98 (NRPN LSB)',
    '99 (NRPN MSB)',
    '100 (RPN LSB)',
    '101 (RPN MSB)',
    '102',
    '103',
    '104',
    '105',
    '106',
    '107',
    '108',
    '109',
    '110',
    '111',
    '112',
    '113',
    '114',
    '115',
    '116',
    '117',
    '118',
    '119',
    '120 (All Sound Off)',
    '121 (Reset All Controllers)',
    '122 (Local Control On/Off)',
    '123 (All Notes Off)',
    '124 (Omni Mode Off)',
    '125 (Omni Mode On)',
    '126 (Mono Mode On)',
    '127 (Poly Mode On)',
]

def send_sysex(port, command, *args):
    port.send(mido.Message('sysex', data=[SYSEX_ID, SYSEX_COMMANDS[command], *args]))

def clamp(x, low, high):
    return max(low, min(high, x))

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title('Breath Controller Configuration Tool')
        self.resizable(height=False, width=False)

        self.bind('q', lambda e: self.destroy())

        self.curve = [(0, 0), (127, 127)]

        self.devices = None
        self.presets = None

        self.frame_device = ttk.Frame(self)
        self.label_device = ttk.Label(self.frame_device, text='Device')
        self.combo_device = ttk.Combobox(self.frame_device, justify='left', state='readonly')
        self.combo_device.bind('<<ComboboxSelected>>', self.device_selected)
        self.button_get_devices = ttk.Button(
            self.frame_device, text='Refresh', command=self.get_devices)
        self.label_device.pack(side='left', padx=(0, 3))
        self.combo_device.pack(side='left', fill='x', expand=1, padx=3)
        self.button_get_devices.pack(side='left', padx=(3, 0))

        self.separator_device = ttk.Separator(self)

        self.frame_middle = ttk.Frame(self)

        self.frame_curve = ttk.Frame(self.frame_middle)
        self.canvas = tk.Canvas(
            self.frame_curve, width=255, height=255, borderwidth=0, highlightthickness=0,
            cursor='tcross', bg='#394146')
        self.canvas.bind('<Button-1>', self.canvas_left_click)
        self.canvas.bind('<B1-Motion>', self.canvas_left_drag)
        self.canvas.bind('<Button-2>', self.canvas_middle_click)
        self.canvas.bind('<Button-3>', self.canvas_right_click)
        self.canvas.bind('<Motion>', self.canvas_motion)
        self.canvas.bind('<Leave>', self.canvas_leave)
        self.label_curve = ttk.Label(self.frame_curve, text='MIDI vs pressure')
        self.canvas.pack(side='top')
        self.label_curve.pack(side='top')

        self.frame_settings = ttk.Frame(self.frame_middle)

        self.frame_midi_channel = ttk.Frame(self.frame_settings)
        self.label_midi_channel = ttk.Label(
            self.frame_midi_channel, text='MIDI channel', width=15)
        self.combo_midi_channel = ttk.Combobox(
            self.frame_midi_channel, justify='left', state='readonly',
            values=list(range(1,17)), width=30)
        self.combo_midi_channel.current(0)
        self.label_midi_channel.pack(side='left')
        self.combo_midi_channel.pack(side='left', fill='x', expand=1)

        self.frame_midi_message = ttk.Frame(self.frame_settings)
        self.label_midi_message = ttk.Label(
            self.frame_midi_message, text='MIDI message', width=15)
        self.combo_midi_message = ttk.Combobox(
            self.frame_midi_message, justify='left', state='readonly',
            values=list(MIDI_MESSAGES.values()), width=30)
        self.combo_midi_message.current(0)
        self.combo_midi_message.bind('<<ComboboxSelected>>', self.midi_message_selected)
        self.label_midi_message.pack(side='left')
        self.combo_midi_message.pack(side='left', fill='x', expand=1)

        self.frame_control_number = ttk.Frame(self.frame_settings)
        self.label_control_number = ttk.Label(
            self.frame_control_number, text='Control number', width=15)
        self.combo_control_number = ttk.Combobox(
            self.frame_control_number, justify='left', state='readonly',
            values=CONTROL_NUMBERS, width=30)
        self.combo_control_number.current(2)
        self.label_control_number.pack(side='left')
        self.combo_control_number.pack(side='left', fill='x', expand=1)

        self.frame_input_gain = ttk.Frame(self.frame_settings)
        self.label_input_gain = ttk.Label(
            self.frame_input_gain, text='Input gain', width=15)
        self.scale_input_gain = ttk.Scale(
            self.frame_input_gain, from_=1.0, to=4.0, orient='horizontal',
            value=1.0, command=self.input_gain_changed)
        self.label_input_gain_current = ttk.Label(
            self.frame_input_gain, width=3, anchor='e')
        self.label_input_gain.pack(side='left')
        self.scale_input_gain.pack(side='left', fill='x', expand=1)
        self.label_input_gain_current.pack(side='left')
        self.input_gain_changed()

        self.separator_presets = ttk.Separator(self.frame_settings)

        self.frame_presets = ttk.Frame(self.frame_settings)
        self.label_presets = ttk.Label(self.frame_presets, text='Preset', width=15)
        self.combo_presets = ttk.Combobox(
            self.frame_presets, justify='left', state='readonly', width=30)
        self.combo_presets.bind('<<ComboboxSelected>>', self.load_preset)
        self.combo_presets.bind('<Button-1>', self.get_presets)
        self.label_presets.pack(side='left')
        self.combo_presets.pack(side='left', fill='x', expand=1)

        self.button_save_preset = ttk.Button(
            self.frame_settings, text='Save preset as', command=self.save_preset)

        self.frame_midi_channel.pack(side='top', fill='x', pady=2)
        self.frame_midi_message.pack(side='top', fill='x', pady=2)
        self.frame_control_number.pack(side='top', fill='x', pady=2)
        self.frame_input_gain.pack(side='top', fill='x', pady=2)
        self.separator_presets.pack(side='top', fill='x', pady=8)
        self.frame_presets.pack(side='top', fill='x', pady=2)
        self.button_save_preset.pack(side='top', anchor='e', pady=8, ipadx=8)

        self.frame_curve.pack(side='left', padx=(0, 10))
        self.frame_settings.pack(side='left', fill='x', expand=1, anchor='n')

        self.separator_bottom = ttk.Separator(self)

        self.frame_bottom = ttk.Frame(self)
        self.button_apply = ttk.Button(
            self.frame_bottom, text='Apply', state='disabled', command=self.apply_settings)
        self.button_save = ttk.Button(
            self.frame_bottom, text='Save permanently', state='disabled',
            command=self.save_settings)
        self.button_save.pack(side='right', padx=(3, 0), ipadx=8)
        self.button_apply.pack(side='right', padx=(0, 3))

        self.frame_device.pack(side='top', fill='x', padx=10, pady=10)
        self.separator_device.pack(side='top', fill='x', padx=10)
        self.frame_middle.pack(side='top', fill='x', padx=10, pady=10)
        self.separator_bottom.pack(side='top', fill='x', padx=10)
        self.frame_bottom.pack(side='top', fill='x', padx=10, pady=10)

        self.get_devices()
        self.get_presets()

        self.draw_grid()
        self.draw_curve()

    def draw_grid(self):
        for g in [63, 127, 191]:
            self.canvas.create_line(g, 0, g, 256, fill='#252d32', tags='grid')
            self.canvas.create_line(0, g, 256, g, fill='#252d32', tags='grid')

    def draw_curve(self):
        self.canvas.delete('point')
        self.canvas.delete('curve')
        self.fix_curve()
        points = [(2*x, 254-2*y) for (x, y) in self.curve]
        self.canvas.create_line(points, width=2, fill='#f3b02e', tags='curve')
        for (x, y) in points:
            self.canvas.create_oval(
                x-3, y-3, x+3, y+3, fill='white', outline='black', tags='point')

    def fix_curve(self):
        if not self.curve:
            self.curve = [(0, 0), (127, 127)]
            return
        self.curve.sort()
        self.curve = [(clamp(x, 0, 127), clamp(y, 0, 127)) for (x, y) in self.curve]
        self.curve = reduce(
            lambda ps, p: ps if ps and ps[-1][0] == p[0] else ps + [p],
            self.curve, [])
        if self.curve[0][0] != 0:
            self.curve.insert(0, (0, self.curve[0][1]))
        if self.curve[-1][0] != 127:
            self.curve.append((127, self.curve[-1][1]))

    def curve_table(self):
        table = []
        for a, b in zip(self.curve, self.curve[1:]):
            for x in range(a[0], b[0]):
                table.append(round(a[1] + (x-a[0])*(b[1]-a[1])/(b[0]-a[0])))
        table.append(self.curve[-1][1])
        return table

    def event_to_point(self, event):
        x = clamp(event.x, 0, 254)
        y = clamp(event.y, 0, 254)
        return (x//2, 127-y//2)

    def canvas_left_click(self, event):
        click_point = self.event_to_point(event)
        adjacent_point = min(self.curve, key=lambda p: abs(p[0] - click_point[0]))
        distance = lambda p, q: abs(p[0]-q[0]) + abs(p[1]-q[1])
        if click_point[0] != adjacent_point[0] and distance(click_point, adjacent_point) > 8:
            self.curve.append(click_point)
            self.draw_curve()

    def canvas_left_drag(self, event):
        drag_point = self.event_to_point(event)
        self.label_curve.configure(text='({}, {})'.format(drag_point[0], drag_point[1]))
        adjacent_point = min(self.curve, key=lambda p: abs(p[0] - drag_point[0]))
        distance = lambda p, q: abs(p[0]-q[0]) + abs(p[1]-q[1])
        closest_point = min(self.curve, key=lambda p: distance(p, drag_point))
        if adjacent_point == closest_point or drag_point[0] != adjacent_point[0]:
            self.curve.remove(closest_point)
            self.curve.append(drag_point)
            self.draw_curve()

    def canvas_right_click(self, event):
        click_point = self.event_to_point(event)
        distance = lambda p, q: abs(p[0]-q[0]) + abs(p[1]-q[1])
        closest_point = min(self.curve, key=lambda p: distance(p, click_point))
        if distance(click_point, closest_point) < 8:
            self.curve.remove(closest_point)
            self.draw_curve()

    def canvas_middle_click(self, event):
        self.curve = [(0,0), (127,127)]
        self.draw_curve()

    def canvas_motion(self, event):
        x, y = self.event_to_point(event)
        self.label_curve.configure(text='({}, {})'.format(x, y))

    def canvas_leave(self, event):
        self.label_curve.configure(text='MIDI vs pressure')

    def device_selected(self, event=None):
        s = 'normal' if self.combo_device.get() != '' else 'disabled'
        self.button_apply.configure(state=s)
        self.button_save.configure(state=s)

    def midi_message_selected(self, event=None):
        s = 'readonly' if self.combo_midi_message.current() == 0 else 'disabled'
        self.combo_control_number.configure(state=s)

    def input_gain_changed(self, event=None):
        self.label_input_gain_current.configure(
            text='{:1.1f}'.format(self.scale_input_gain.get()))

    def apply_settings(self):
        try:
            with mido.open_output(self.combo_device.get()) as port:
                send_sysex(port, 'set_midi_channel', 1 + self.combo_midi_channel.current())
                send_sysex(port, 'set_midi_message', self.combo_midi_message.current())
                send_sysex(port, 'set_control_number', self.combo_control_number.current())
                send_sysex(port, 'set_input_gain', round(10 * self.scale_input_gain.get()))
                send_sysex(port, 'set_curve', *self.curve_table())
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def save_settings(self):
        self.apply_settings()
        try:
            with mido.open_output(self.combo_device.get()) as port:
                send_sysex(port, 'save_to_eeprom')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def get_devices(self):
        try:
            self.devices = [d for d in mido.get_output_names()
                if d.find('Breath Controller') != -1]
        except Exception as e:
            self.devices = []
            messagebox.showerror('Error', str(e))
        finally:
            self.combo_device.configure(values=self.devices)
            self.combo_device.set(self.devices[0] if self.devices else '')
            self.device_selected()

    def get_presets(self, event=None):
        preset_files = sorted(glob.glob('presets/*.preset'))
        preset_names = [os.path.splitext(os.path.basename(f))[0] for f in preset_files]
        self.presets = dict(zip(preset_names, preset_files))
        self.combo_presets.configure(values=preset_names)

    def load_preset(self, event=None):
        try:
            with open(self.presets[self.combo_presets.get()], 'r') as f:
                for line in f:
                    kv = line.split()
                    if len(kv) == 2:
                        k, v = kv
                        if (k == 'midi_channel'):
                            if 1 <= int(v) <= 16:
                                self.combo_midi_channel.set(v)
                        elif (k == 'midi_message'):
                            if v in MIDI_MESSAGES.keys():
                                self.combo_midi_message.set(MIDI_MESSAGES[v])
                                self.midi_message_selected()
                        elif (k == 'control_number'):
                            if 0 <= int(v) <= 127:
                                self.combo_control_number.set(CONTROL_NUMBERS[int(v)])
                        elif (k == 'input_gain'):
                            if 1.0 <= float(v) <= 4.0:
                                self.scale_input_gain.set(float(v))
                    elif len(kv) > 2:
                        k, v = kv[0], ''.join(kv[1:])
                        if (k == 'curve'):
                            if re.fullmatch(r'(\(\d+,\d+\)){2,}', v):
                                self.curve = []
                                for p in re.finditer(r'\((\d+),(\d+)\)', v):
                                    self.curve.append((int(p.group(1)), int(p.group(2))))
                                self.draw_curve()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def save_preset(self):
        file_name = filedialog.asksaveasfilename(
            initialdir='presets', defaultextension='.preset',
            filetypes=(('Presets', '*.preset'), ('All files', '*')))
        if file_name:
            try:
                with open(file_name, 'w') as f:
                    f.write('midi_channel {}\n'.format(self.combo_midi_channel.current() + 1))
                    midi_message = [k for k in MIDI_MESSAGES.keys()
                        if MIDI_MESSAGES[k] == self.combo_midi_message.get()][0]
                    f.write('midi_message {}\n'.format(midi_message))
                    if midi_message == 'control_change':
                        f.write('control_number {}\n'.format(self.combo_control_number.current()))
                    f.write('input_gain {:1.1f}\n'.format(self.scale_input_gain.get()))
                    f.write('curve {}\n'.format(
                        ' '.join(['({},{})'.format(x, y) for (x, y) in self.curve])))
            except Exception as e:
                messagebox.showerror('Error', str(e))
            else:
                self.get_presets()

if __name__ == '__main__':
    mido.set_backend('mido.backends.rtmidi')
    App().mainloop()
