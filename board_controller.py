from machine import Timer, Pin
import ujson as json
from ble_controller import BleController
import utime as time
from urandom import choice

import sensors


__version__ = "1.0.0"

# check if there is a device name
try:
    with open('.mac', 'r') as f:
        MAC = f.read()
except Exception:
    MAC = ''.join([choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(16)])
    with open('.mac', 'w') as f:
        f.write(MAC)

# check if a config file exists
try:
    with open('config.json', 'r') as f:
        CONFIG = json.load(f)
except Exception:
    CONFIG = {
        'ble_name': 'Lass Mich',
        'notify_interval': 5000,
        'sensors': {
            'random': {
                'name': 'random',
                '_func': 'random_integer', 
                'kwargs': {}
            }
        }
    }


class BoardController:
    """Board controller"""
    def __init__(self, debug=False, button_pin = 27):
        # initialze the bluetooth controller
        self.ble_controller = BleController(
            CONFIG.get('ble_name', 'Stupid Nameless Device'),
            connect_callbacks=[self.start],
            disconnect_callbacks=[self.stop],
            write_callbacks=[self.debug_receive],
            debug=debug
        )

        # initialize the timer
        self.timer = Timer(1)

        # button
        self.button = Pin(button_pin, Pin.IN)

        # set the debug flag
        self.debug = debug

    def start(self):
        """Start the timer to periodically send data over BLE"""
        # This might be replaced by updating the advertised data
        self.timer.init(period=CONFIG.get('notify_interval', 100000), mode=Timer.PERIODIC, callback=self.sense)

        if self.debug:
            print('[BOARD CONTROLLER] started')

    def stop(self):
        self.timer.deinit()

    def sense(self, irq_pin = None):
        """Send all configured data over BLE"""
        data = {
            'firmware': __version__,
            '_id': MAC
        }

        # get all sensor names
        sensor_names = CONFIG.get('sensors', [])
        if len(sensor_names) == 0:
            data = {'error': 'No sensors configured'}

        # load all sensors
        for sensor in sensor_names:
            # get the sensor props
            name = sensor['name']
            func_name = sensor.get('_func', '__NO_FUNC_PROVIDED')

            # check if a interface is defined
            if not hasattr(sensors, func_name):
                data[name] = f"Interface {func_name} not found for sensor {name}."
            else:
                # get the sensor function
                func = getattr(sensors, func_name)
                d1 = time.ticks_ms()
                try:
                    value = func(self, **sensor.get('kwargs', {}))
                    d2 = time.ticks_ms()
                    data[name] = {'value': value, 'runtime': d2 - d1}
                except Exception as e:
                    data[name] = f"Error while reading sensor {name}: {e}"

        # turn to JSON
        payload = json.dumps(data)

        # send
        self.ble_controller.send(payload)

        # debug message
        if self.debug:
            print(f"[BOARD CONTROLLER] SEND: {payload}")

    def send(self, message: str):
        """Send a message over BLE"""
        self.ble_controller.send(message)

    def debug_receive(self, data: str):
        print(f"[BOARD CONTROLLER] DEBUG: {data}")

        # check the payload
        payload = json.loads(data)
        if 'config' in payload:

            # check if there is an update
            if payload['config'] != 'get':
                self.set_config(payload['config'])
            
            conf = json.dumps({'config': self.get_config()})
            self.send(conf)
        
        # handle sensor updates
        if 'sensor' in payload:
            # check if this is an update
            if payload['sensor'] != 'get':
                self.set_sensor(payload['sensor'])

            conf = json.dumps({'config': self.get_config()})
            self.send(conf)

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
    
    def set_sensor(self, sensor):
        if isinstance(sensor, str):
            sensor = json.loads(sensor)
        
        # update the sensor config
        CONFIG['sensors'].update(sensor)

        with open('config.json', 'w') as f:
            json.dump(CONFIG, f, indent=4)
