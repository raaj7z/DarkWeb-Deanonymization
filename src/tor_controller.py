import time
from utils import success, error, info, warn

class TorController:
    """Optional Tor control-port client. Data traffic remains SOCKS-routed."""

    def __init__(self, port=9051, password=''):
        self.port = port
        self.password = password
        self._controller = None
        self.circuit_count = 0
        self.connect()

    def _connect(self):
        try:
            from stem.control import Controller
            self._controller = Controller.from_port(port=self.port)
            if self.password:
                self._controller.authenticate(password=self.password)
            else:
                self._controller.authenticate()
            success("Tor controller connected")
            return True
        except ImportError:
            warn("stem not installed — circuit rotation disabled")
        except Exception as e:
            warn(f"Tor controller unavailable: {e}")
            warn("Circuit rotation is optional; SOCKS crawling can still run.")
        self._controller = None
        return False

    def connect(self):
        return self._connect()

    def is_connected(self):
        return self._controller is not None

    def new_circuit(self, wait_seconds=1):
        if not self._controller:
            return False
        try:
            from stem import Signal
            self._controller.signal(Signal.NEWNYM)
            self.circuit_count += 1
            if wait_seconds:
                time.sleep(wait_seconds)
            info(f"New Tor circuit #{self.circuit_count}")
            return True
        except Exception as e:
            error(f"Circuit rotation failed: {e}")
            self._controller = None
            return False

    def rotate_every(self, requests_count, current_count):
        if requests_count > 0 and current_count > 0 and current_count % requests_count == 0:
            return self.new_circuit()
        return False

    def close(self):
        if self._controller:
            try:
                self._controller.close()
            except Exception:
                pass
            self._controller = None
