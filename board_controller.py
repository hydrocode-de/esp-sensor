from machine import Timer
import esp
import ujson as json
from ble_controller import BleController
from random import random

# check if a config file exists
try:
    with open('config.json', 'r') as f:
        CONFIG = json.load(f)
except Exception:
    CONFIG = {
        'ble_name': 'Lass Mich',
        'notify_interval': 5000
    }

class BoardController:
    def __init__(self):
        # initialze the bluetooth controller
        self.ble_controller = BleController(
            CONFIG.get('ble_name', 'Stupid Nameless Device'),
            connect_callbacks=[self.start],
            disconnect_callbacks=[self.stop],
            write_callbacks=[self.debug_receive]
        )
        
        # initialize the timer
        self.timer = Timer(1)
    
    def start(self):
        """Start the timer to periodically send data over BLE"""
        # This might be replaced by updating the advertised data
        self.timer.init(period=CONFIG.get('notify_interval', 100000), mode=Timer.PERIODIC, callback=self.sense)

    def stop(self):
        self.timer.deinit()

    def internal_temp(self, unit='C'):
        """Internal temperature in Celsius or Fahrenheit"""
        return random() * 100
    
    def sense(self, irq_pin = None):
        """Send all configured data over BLE"""
        data = {
            'internal_temp': self.internal_temp()
        }

        # turn to JSON
        payload = json.dumps(data)
        
        # send
        self.ble_controller.send(payload)

    def send(self, message: str):
        """Send a message over BLE"""
        self.ble_controller.send(message)

    def debug_receive(self, data: str):
        print(f"[BOARD CONTROLLER] DEBUG: {data}")

        # check the payload
        payload = json.loads(data)
        if 'config' in payload:
            if payload['config'] == 'get':
                self.send(self.get_config())
            else:
                self.set_config(payload['config'])
        
    def get_config(self):
        c = json.dumps(CONFIG)
        return c
    
    def set_config(self, config):
        if isinstance(config, str):
            config = json.loads(config)
        
        # update config
        CONFIG.update(config)

        with open('config.json', 'w') as f:
            json.dump(CONFIG, f, indent=4)