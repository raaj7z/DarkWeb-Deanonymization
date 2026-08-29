
import time
import random
from utils import get_tor_session, success, error, info, warn

class AliveChecker:
    
    def __init__(self, timeout=30, retries=3):
        self.timeout = timeout
        self.retries = retries
        self.session = get_tor_session()
    
    def check(self, url):
        """Check if a single onion URL is alive"""
        for attempt in range(self.retries):
            try:
             
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    success(f"ALIVE [{response.status_code}] {url}")
                    return {
                        'url': url,
                        'alive': True,
                        'status_code': response.status_code,
                        'content_length': len(response.content),
                        'server': response.headers.get('Server', 'Unknown'),
                        'title': self._extract_title(response.text)
                    }
                
                elif response.status_code in [301, 302]:
                    redirect = response.headers.get('Location', '')
                    warn(f"REDIRECT {url} → {redirect}")
                    return {
                        'url': url,
                        'alive': True,
                        'status_code': response.status_code,
                        'redirect': redirect
                    }
                
                else:
                    warn(f"RESPONDED [{response.status_code}] {url}")
                    return {
                        'url': url,
                        'alive': False,
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                if attempt < self.retries - 1:
                    warn(f"Attempt {attempt+1} failed for {url}: {e}")
                    self.session = get_tor_session()
                    time.sleep(random.uniform(3, 7))
                else:
                    error(f"DEAD after {self.retries} attempts: {url}")
                    return {
                        'url': url,
                        'alive': False,
                        'error': str(e)
                    }
    
    def check_multiple(self, urls):
        results = {'alive': [], 'dead': []}
        
        info(f"Checking {len(urls)} URLs...")
        
        for i, url in enumerate(urls):
            info(f"[{i+1}/{len(urls)}] Checking: {url}")
            result = self.check(url)
            
            if result and result.get('alive'):
                results['alive'].append(result)
            else:
                results['dead'].append(result)
        
        success(f"Done! Alive: {len(results['alive'])} | Dead: {len(results['dead'])}")
        return results
    
    def _extract_title(self, html):
      
        try:
            import re
            title = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            return title.group(1).strip() if title else 'No title'
        except:
            return 'No title'
