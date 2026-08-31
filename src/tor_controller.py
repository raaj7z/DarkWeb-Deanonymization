# tor_controller.py — Control Tor for circuit rotation
import time
import random
from utils import success, error, info, warn

class TorController:
    
    def init(self, port=9051, password=''):
        self.port = port
        self.password = password
        self.controller = None
        self.circuit_count = 0
        self._connect()
    
    def _connect(self):
        """Connect to Tor control port"""
        try:
            from stem import Signal
            from stem.control import Controller
            
            self.controller = Controller.from_port(port=self.port)
            self.controller.authenticate(password=self.password)
            success("Tor controller connected")
            return True
            
        except Exception as e:
            warn(f"Tor controller unavailable: {e}")
            warn("Circuit rotation disabled — using session refresh instead")
            self.controller = None
            return False
    
    def new_circuit(self):
        """Request new Tor circuit — changes exit node IP"""
        if self.controller:
            try:
                from stem import Signal
                self.controller.signal(Signal.NEWNYM)
                self.circuit_count += 1
                # Wait for new circuit to be established
                time.sleep(5)
                success(f"New Tor circuit #{self.circuit_count}")
                return True
            except Exception as e:
                error(f"Circuit rotation failed: {e}")
                return False
        else:
            warn("No controller — using session refresh")
            return False
    
    def rotate_every(self, requests_count, current_count):
        """Rotate circuit every N requests"""
        if current_count > 0 and current_count % requests_count == 0:
            info(f"Rotating circuit after {requests_count} requests")
            return self.new_circuit()
        return False
    
    def get_current_ip(self, session):
        """Get current Tor exit IP"""
        try:
            r = session.get('http://ifconfig.me', timeout=15)
            return r.text.strip()
        except:
            return "Unknown"
    
    def enable_tor_control(self):
        """
        Setup instructions — run these in Ubuntu:
        
        1. Edit torrc:
           sudo nano /etc/tor/torrc
           
        2. Add these lines:
           ControlPort 9051
           HashedControlPassword (generate with: tor --hash-password "yourpassword")
           
        3. Restart Tor:
           sudo service tor restart
        """
        info("To enable Tor control port:")
        info("1. sudo nano /etc/tor/torrc")
        info("2. Add: ControlPort 9051")
        info("3. Add: CookieAuthentication 1")
        info("4. sudo service tor restart")
    
    def close(self):
        if self.controller:
            self.controller.close()
