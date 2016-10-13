""" Switch controller for Raspberry Pi
"""
from __future__ import print_function

import time
from multiprocessing import Process

from RPi import GPIO


class Switches(object):
    """ Object to hold all switch state and actions
    """
    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        self._shutdown = False

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
        switch = Process(
            target=self._monitor_switch,
            args=(
                switch,
                on_callback,
                off_callback
            )
        )
        switch.start()

    def shutdown(self):
        """ Shutdown all switch instances
        """
        self._shutdown = True


def _call_on():
    print("Call On")


def _call_off():
    print("Call Off")


def main():
    """ Main entry point
    """
    switches = Switches()
    switches.monitor_switch(18, _call_on, _call_off)

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt as error:
        print("Received KeyboardInterrupt: %s" % error)
        switches.shutdown()


if __name__ == "__main__":
    main()
