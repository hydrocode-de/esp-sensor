from machine import Pin, Timer
from neopixel import NeoPixel
import time
import ubluetooth as bluetooth

# init the LED
rgb = NeoPixel(Pin(27), 1)


# pre-define some colors
COLORS = dict(red=(128, 0, 0), green=(0,128, 0), blue=(0,0,128), white=(128, 128, 128), off=(0,0,0))
def color(neo, rgb):
    if isinstance(rgb, str):
        rgb = COLORS.get(rgb, (128, 128, 128))
    
    # set color
    neo[0] = rgb
    neo.write()


def toggleRGB(pin, col='blue'):
    curr = rgb[0]
    if curr == COLORS.get('off'):
        color(rgb, col)
    if curr == COLORS.get(col):
        color(rgb, 'off')


class BleController:
    def __init__(self, name: str, connect_callbacks=[], disconnect_callbacks=[], write_callbacks=[], debug=False):
        self.name = name
        self.timer = Timer(0)
        self.debug = debug

        # instantiate the bluetooth controller
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.status = 0

        # on init, the device is disconnected
        self.disconnected()

        # register the bluetooth interrupt
        self.ble.irq(self.irq)

        # register and advertise
        self.register()
        self.advertiser()

        # callbacks
        self.connect_callbacks = connect_callbacks
        self.disconnect_callbacks = disconnect_callbacks
        self.write_callbacks = write_callbacks

        if self.debug:
            print('[BLE Controller] initialized')


    def connected(self):
        """BLE is connected, indicate by 3 fast green flashs"""
        self.timer.deinit()

        def connect_blink_green():  
            color(rgb, 'off')
            time.sleep_ms(200)
            color(rgb, 'green')
            time.sleep_ms(200)
            color(rgb, 'off')

        # connect blink
        for i in range(3):
            connect_blink_green()
        
        # signaller
        self.timer.init(period=60000, mode=Timer.PERIODIC, callback=connect_blink_green)

    def disconnected(self):
        """BLE is disconnected, indicate by flashing blue"""
        self.timer.deinit()
        self.timer.init(period=500, mode=Timer.PERIODIC, callback=lambda p: toggleRGB(p, 'blue'))

    def irq(self, event, data):
        """The BLE received an interrupt. This can be a connect, disconnect or write event"""
        # The BLE was connected
        if event == 1:
            if self.debug:
                print('[BLE Controller] device connected')
            self.connected()
            self.status = 1

            # call the connect callbacks
            for callback in self.connect_callbacks:
                callback()

        # the BLE was disconnected
        elif event == 2:
            if self.debug:
                print('[BLE Controller] device disconnected')
            self.advertiser()
            self.disconnected()
            self.status = 0

            # call the disconnect callbacks
            for callback in self.disconnect_callbacks:
                callback()

        # A client device has sent some data
        elif event == 3:
            buffer = self.ble.gatts_read(self.rx)
            m = buffer.decode('UTF-8').strip()
            if self.debug:
                print(f"[BLE Controller] received: {m}")

            # call the write callbacks
            for callback in self.write_callbacks:
                callback(m)

    def register(self):
        # specify uuids for the service
        UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
        UART_TX = (bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E'), bluetooth.FLAG_NOTIFY | bluetooth.FLAG_READ )
        UART_RX = (bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E'), bluetooth.FLAG_WRITE, )

        # define the service
        UART_SERVICE = (UART_UUID, (UART_TX, UART_RX,),)

        # define all services
        SERVICES = (UART_SERVICE, )

        # register
        ((self.tx, self.rx, ), ) = self.ble.gatts_register_services(SERVICES)

    def send(self, data):
        if self.status == 1:
            self.ble.gatts_notify(0, self.tx, data + '\n')
        else: 
            print('[BLE Controller] not connected')

    def advertiser(self):
        # convert the name to bytes and create advertise data array
        name = bytes(self.name, 'UTF-8')
        adv_data = bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name

        # advertise
        self.ble.gap_advertise(200, adv_data)
        if self.debug:
            print(adv_data)
