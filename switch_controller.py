""" Switch controller for Raspberry Pi
"""
from __future__ import division, print_function

import math
import time
import threading

import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
import Adafruit_PCA9685

from RPi import GPIO
from flask.views import MethodView
from flask import jsonify, Flask


SWITCH_API = Flask(__name__)

LED_CONTROLLER = Adafruit_PCA9685.PCA9685()

SPI_PORT = 0
SPI_DEVICE = 0
MCP = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))


def _convert_percent_to_dec(percent):
    """ Convert a percentage to a decimal. IE. 100% = 1.0, 50% = 0.5
    """
    dec = percent/100

    return dec


def _init_controller():
    """ Initilize the LED controller.
    """
    LED_CONTROLLER.set_pwm_freq(1525)


def _check_rgb_types(red, green, blue):
    return bool(
        isinstance(red, int) and
        isinstance(green, int) and
        isinstance(blue, int)
    )


def _change_leds(red, green, blue):
    """ Change LED brightness
    """
    if _check_rgb_types(red, green, blue):
        red = int(4095*_convert_percent_to_dec(red))
        green = int(4095*_convert_percent_to_dec(green))
        blue = int(4095*_convert_percent_to_dec(blue))
    else:
        raise TypeError("Expected variable type INT")

    LED_CONTROLLER.set_pwm(0, 0, red)
    LED_CONTROLLER.set_pwm(1, 0, green)
    LED_CONTROLLER.set_pwm(2, 0, blue)


class SwitchAPI(MethodView):
    """ API for controlling LEDs.
    """
    def get(self):  # pylint: disable=no-self-use
        """ Get current state of LED settings.
        """
        switch_state = {
            "is_on": _SWITCHES.is_on,
            "change": _SWITCHES.change,
            "red": _SWITCHES.red,
            "green": _SWITCHES.green,
            "blue": _SWITCHES.blue,
        }

        _SWITCHES.change_state(False)

        return jsonify(switch_state)

SWITCH_API.add_url_rule('/switches/', view_func=SwitchAPI.as_view('switchess'))


class Switches(object):
    """ Object to hold all switch state and actions
    """
    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        self.is_on = False
        self.change = False

        self.red = 0
        self.green = 0
        self.blue = 0

        self.run = True
        self._switch_state = False

    def _monitor_switch(self, switch, on_callback, off_callback):
        prev_state = False

        while self.run:
            state = GPIO.input(switch)

            if state != prev_state and state:
                off_callback()
            elif state != prev_state and not state:
                on_callback()

            prev_state = state
            time.sleep(0.1)

    def monitor_switch(self, switch, on_callback, off_callback):
        """ Monitor switch on GPIO of switch. If closed runs on_callback if
        open runs off_callback.
        """
        if not isinstance(switch, int):
            raise TypeError("switch not of type int")

        if not callable(on_callback):
            raise TypeError("on_callback is not callable")

        if not callable(off_callback):
            raise TypeError("off_callback is not callable")

        GPIO.setup(switch, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        switch = threading.Thread(
            target=self._monitor_switch,
            args=(
                switch,
                on_callback,
                off_callback
            )
        )
        switch.start()

    def get_state(self):
        """ Return bool of if switch state has changed or not
        """
        return self._switch_state

    def change_state(self, state):
        """ Return bool of if switch state has changed or not
        """
        self._switch_state = state

    def shutdown(self):
        """ Shutdown all switch instances
        """
        self.run = False


def _start_flask():
    flask_app = threading.Thread(
        target=SWITCH_API.run,
        kwargs=dict(
            host='0.0.0.0',
            port=8080
        )
    )
    flask_app.start()


def _start_rgb():
    while _SWITCHES.run:
        values = [0, 0, 0]

        for i in range(3):
            values[i] = MCP.read_adc(i)

        red = int(math.floor(values[0]/1024*100))
        green = int(math.floor(values[1]/1024*100))
        blue = int(math.floor(values[2]/1024*100))

        _SWITCHES.red = red
        _SWITCHES.green = green
        _SWITCHES.blue = blue

        _change_leds(
            red,
            green,
            blue
        )

        time.sleep(.1)


def _start_rgb_thread():
    flask_app = threading.Thread(
        target=_start_rgb
    )
    flask_app.start()


def _on_off_switch_on():
    _SWITCHES.is_on = True


def _on_off_switch_off():
    _SWITCHES.is_on = False


def _rgb_switch_on():
    _SWITCHES.change = True


def _rgb_switch_off():
    _SWITCHES.change = False


def main():
    """ Main entry point
    """
    _SWITCHES.monitor_switch(17, _rgb_switch_on, _rgb_switch_off)
    _SWITCHES.monitor_switch(18, _on_off_switch_on, _on_off_switch_off)
    _start_rgb_thread()
    _start_flask()

    try:
        while _SWITCHES.run:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        _SWITCHES.shutdown()


if __name__ == "__main__":
    _STATE_CHANGE = False
    _SWITCHES = Switches()

    main()
