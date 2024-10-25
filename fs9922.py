import serial
from serial.tools import list_ports

ports = list_ports.comports()
fs9922_port = None

class Flag:
    def __init__(self, name, byte, bit):
        self.name = name
        self.en = False
        self.byte = byte
        self.bit = bit

    def update(self, packet):
        self.en = packet[self.byte] & (1 << self.bit)

class FS9922_DMM3:
    def __init__(self):
        self.sign = '+'
        self.data = "0000" 
        self.point = 0
        self.prefixes = [Flag('n', 0x8, 1), Flag('µ', 0x9, 7), Flag('m', 0x9, 6), Flag('k', 0x9, 5), Flag('M', 0x9, 4)]
        self.units = [Flag('℉', 0xA, 0), Flag('℃', 0xA, 1), Flag('F', 0xA, 2), Flag('Hz', 0xA, 3), Flag('hFE', 0xA, 4), Flag('Ω', 0xA, 5), Flag('A', 0xA, 6), Flag('V', 0xA, 7), Flag('%', 0x9, 1)]
        self.modes = [Flag('AC', 0x7, 3), Flag('DC', 0x7, 4), Flag('Beep', 0x9, 3), Flag('Diode', 0x9, 2)]
        self.measure_modes = [Flag('HOLD', 0x7, 1), Flag('REL', 0x7, 2), Flag('MIN', 0x8, 4), Flag('MAX', 0x8, 5)]

    def update(self, packet):
        self.sign = packet[0]
        self.data = " 0L " if packet[1:5].decode("utf-8") == "?0:?" else packet[1:5].decode("utf-8")
        self.point = 3 if packet[6] == 0x34 else int(packet[6]) - 0x30

        for attrib_flag in (self.prefixes + self.units + self.modes + self.measure_modes):
            attrib_flag.update(packet)
    
    def get_data_str(self):
        data_str = self.data
        if data_str == " 0L ":
            return data_str

        if(self.point > 0):
            data_str = data_str[:self.point] + '.' + data_str[self.point:]
        
        return data_str

    def get_data_float(self):
        return float(self.get_data_str())

    def get_data_int(self):
        return int(self.get_data_str())

    def get_unit(self):
        for unit in self.units:
            if unit.en:
                return unit.name

        return '' 

    def get_mode(self):
        for mode in self.modes:
            if mode.en:
                return mode.name

        return ''

    def get_prefix(self):
        for prefix in self.prefixes:
            if prefix.en:
                return prefix.name

        return '' 

if __name__ == "__main__":
    for port, desc, hwid in sorted(ports):
        print(f"{port}: {desc} [{hwid}]")
    
    while(fs9922_port == None):
        print("Select serial port (enter name):")
        port_name = input()
        for port, desc, hwid in sorted(ports):
            if port_name == port:
                fs9922_port = port_name

        if(fs9922_port == None):
            print(f"Couldn't find {port_name}. Please enter different name:")

        dmm = FS9922_DMM3()

        with serial.Serial(fs9922_port, 2400) as ser:
            while True:
                line = ser.readline()
                dmm.update(line)
                print(dmm.get_data_str(), dmm.get_prefix() + dmm.get_unit(), dmm.get_mode())
