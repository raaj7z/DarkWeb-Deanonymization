# tor_controller.py — FIXED v2
# P0 FIX: init typo fixed
# P0 FIX: Proper connect() method added
# P0 FIX: Clear error messages on failure

import time
import random
from utils import success, error, info, warn

class TorController:

    def init(self, port=9051, password=''):
        """
        FIXED: was 'init' before — caused silent initialization failure
        """
        self.port     = port
        self.password = password
        self._controller = None
        self.circuit_count = 0
        self._connect()

    def _connect(self):
        """Connect to Tor control port"""
        try:
            from stem import Signal
            from stem.control import Controller

            self._controller = Controller.from_port(port=self.port)
            self._controller.authenticate(password=self.password)
            success("Tor controller connected")
            return True

        except ImportError:
            warn("stem not installed — run: pip3 install stem")
            warn("Circuit rotation disabled")
            self._controller = None
            return False

        except Exception as e:
            warn(f"Tor controller unavailable: {e}")
            warn("To enable: add 'ControlPort 9051' to /etc/tor/torrc")
            warn("Then: sudo service tor restart")
            self._controller = None
            return False

    def connect(self):
        """Public connect method — call to retry connection"""
        return self._connect()

    def is_connected(self):
        """Check if controller is active"""
        return self._controller is not None

    def new_circuit(self):
        """Request new Tor circuit — changes exit node IP"""
        if not self._controller:
            warn("No Tor controller — session refresh only")
            return False
        try:
            from stem import Signal
            self._controller.signal(Signal.NEWNYM)
            self.circuit_count += 1
            time.sleep(5)
            success(f"New Tor circuit #{self.circuit_count}")
            return True
        except Exception as e:
            error(f"Circuit rotation failed: {e}")
            # Try reconnecting
            self._connect()
            return False

    def rotate_every(self, requests_count, current_count):
        """Rotate circuit every N requests"""
        if current_count > 0 and current_count % requests_count == 0:
            info(f"Rotating after {requests_count} requests")
            return self.new_circuit()
        return False

    def get_current_ip(self, session):
        """Get current Tor exit IP"""
        try:
            r = session.get('http://ifconfig.me', timeout=15)
            return r.text.strip()
        except:
            return "Unknown"

    def close(self):
        if self._controller:
            try:
                self._controller.close()
                info("Tor controller closed")
            except:
                pass
