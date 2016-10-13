""" Switch controller for Raspberry Pi
"""
from __future__ import print_function

import time
import threading

from RPi import GPIO
from flask.views import MethodView
from flask import jsonify, Flask


SWITCH_API = Flask(__name__)


class SwitchAPI(MethodView):
    """ API for controlling LEDs.
    """
    def get(self):  # pylint: disable=no-self-use
        """ Get current state of LED settings.
        """
        switch_state = {
            "state_change": _SWITCHES.get_state()
        }

        _SWITCHES.change_state(False)

        return jsonify(switch_state)

SWITCH_API.add_url_rule('/switches/', view_func=SwitchAPI.as_view('switchess'))


class Switches(object):
    """ Object to hold all switch state and actions
    """
    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        self._shutdown = False
        self._switch_state = False

    def _monitor_switch(self, switch, on_callback, off_callback):
        prev_state = False

        while self._shutdown is False:
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
        self._shutdown = True


def _start_flask():
    flask_app = threading.Thread(
        target=SWITCH_API.run,
        kwargs=dict(
            host='0.0.0.0',
            port=8080
        )
    )
    flask_app.start()


def _switch_callback():
    _SWITCHES.change_state(True)


def main():
    """ Main entry point
    """
    _SWITCHES.monitor_switch(18, _switch_callback, _switch_callback)
    _start_flask()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt as error:
        print("Received KeyboardInterrupt: %s" % error)
        _SWITCHES.shutdown()


if __name__ == "__main__":
    _STATE_CHANGE = False
    _SWITCHES = Switches()

    main()
