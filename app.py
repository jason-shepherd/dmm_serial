from flask import Flask
from flask import Response, render_template
from fs9922 import FS9922_DMM3
import serial
from serial.tools import list_ports
import threading
from queue import Queue
import signal
import sys

app = Flask(__name__)

stop_event = threading.Event()
clients = set()
clients_lock = threading.Lock()

def read_serial():
    dmm_port = None
    dmm = FS9922_DMM3() 
    ports = list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print(f"{port}: {desc} [{hwid}]")
    
    while(dmm_port == None):
        print("Select serial port (enter name):")
        port_name = input()
        for port, desc, hwid in sorted(ports):
            if port_name == port:
                dmm_port = port_name

        if(dmm_port == None):
            print(f"Couldn't find {port_name}. Please enter different name:")
    
    print("Selected port:", dmm_port)
    if(dmm_port == None):
        return

    with serial.Serial(dmm_port, 2400, timeout=1) as ser:
        while not stop_event.is_set():
            line = ser.readline()
            if(len(line) == 0):
                continue

            dmm.update(line)
            with clients_lock:
                for client in clients:
                    client.put_nowait(dmm.serialize())

read_thread = threading.Thread(target=read_serial)
read_thread.start()

def exit_handler(sig, frame):
    print("Shutting down...")
    stop_event.set()
    sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGTERM, exit_handler)

@app.route("/")
def root():
    return render_template('index.html')

@app.route("/dmm_stream")
def dmm_stream():
    def eventStream():
        yield ": keepalive\n\n"
        queue = Queue()
        with clients_lock:
            clients.add(queue)

        try:
            while True:
                data = queue.get()
                print(data)
                yield f"data: {data}\n\n"
        finally:
            with clients_lock:
                clients.remove(queue)

    return Response(eventStream(), mimetype="text/event-stream")
