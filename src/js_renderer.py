# Render JavaScript heavy pages using Selenium
import time
import random
from utils import success, error, info, warn

class JSRenderer:
    
    def init(self):
        self.driver = None
        self.available = False
        self._setup()
    
    def _setup(self):
        """Setup Selenium with Chromium through Tor"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            options = Options()
            
            # Run headless — no GUI needed
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            # Route through Tor SOCKS5
            options.add_argument('--proxy-server=socks5://127.0.0.1:9050')
            
            # Anti-detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Random window size — avoid fingerprinting
            width  = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            options.add_argument(f'--window-size={width},{height}')
            
            # Random user agent
            agents = [
                'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0',
                'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
            ]
            options.add_argument(f'user-agent={random.choice(agents)}')
            
            # Try to find chromedriver
            try:
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=options)
            except:
                self.driver = webdriver.Chrome(options=options)
            
            # Hide automation flag
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            self.available = True
            success("JS Renderer ready (Selenium + Chromium)")
            
        except Exception as e:
            warn(f"JS Renderer unavailable: {e}")
            warn("Install: sudo apt install chromium-browser chromium-chromedriver -y")
            self.available = False
    
    def render(self, url, wait_time=5, scroll=True):
        """
        Render a JavaScript page and return full HTML
        Handles: dynamic content, lazy loading, JS-rendered usernames
        """
        if not self.available:
            warn("JS Renderer not available — using requests fallback")
            return None
        
        try:
            info(f"JS rendering: {url[:60]}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(wait_time)
            
            # Simulate human scrolling — triggers lazy load
            if scroll:
                self._human_scroll()
            
            # Wait for dynamic content
            time.sleep(random.uniform(2, 4))
            
            # Get fully rendered HTML
            html = self.driver.page_source
            title = self.driver.title
            
            success(f"JS rendered: {title[:40]}")
            return {
                'html': html,

'title': title,
                'url': self.driver.current_url,
                'rendered': True
            }
            
        except Exception as e:
            error(f"JS render failed: {e}")
            return None
    
    def _human_scroll(self):
        """Simulate human-like scrolling behavior"""
        try:
            # Get page height
            total_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )
            
            # Scroll in chunks like a human
            current = 0
            chunk = random.randint(300, 600)
            
            while current < total_height:
                current += chunk
                self.driver.execute_script(
                    f"window.scrollTo(0, {current});"
                )
                # Random pause between scrolls
                time.sleep(random.uniform(0.5, 1.5))
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            
        except:
            pass
    
    def take_screenshot(self, filename):
        """Take screenshot of rendered page — useful for reports"""
        if not self.available:
            return None
        try:
            import os
            os.makedirs('reports/screenshots', exist_ok=True)
            path = f"reports/screenshots/{filename}.png"
            self.driver.save_screenshot(path)
            success(f"Screenshot: {path}")
            return path
        except Exception as e:
            error(f"Screenshot failed: {e}")
            return None
    
    def close(self):
        if self.driver:
            self.driver.quit()
            info("JS Renderer closed")
