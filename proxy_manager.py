import os
import requests
import random
import logging
from typing import List, Dict, Optional

class ProxyManager:
    """
    Class to manage and rotate proxies for the voting bot.
    Supports both free public proxies and custom proxy lists.
    """
    
    def __init__(self):
        self.proxies = []
        self.custom_proxies = []
        self.last_used_index = -1
        self.logger = logging.getLogger(__name__)
    
    def load_custom_proxies(self, proxy_list: List[str]) -> None:
        """
        Load a list of custom proxies in the format: ip:port or ip:port:username:password
        """
        self.custom_proxies = proxy_list
        self.logger.info(f"Loaded {len(proxy_list)} custom proxies")
    
    def get_free_proxies(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Fetch free proxies from public API
        """
        proxies = []
        
        try:
            # Try to get free proxies from public API
            self.logger.info("Fetching free proxies from public APIs...")
            
            # Free Proxy List API
            response = requests.get('https://www.proxy-list.download/api/v1/get?type=http', timeout=10)
            if response.status_code == 200:
                # Format: IP:PORT on each line
                ip_list = response.text.strip().split('\r\n')
                for ip in ip_list[:limit]:
                    if ':' in ip:
                        proxies.append({
                            'http': f'http://{ip}',
                            'https': f'http://{ip}'
                        })
            
            # Alternative source if first one doesn't work well
            if len(proxies) < 5:
                response = requests.get('https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all', timeout=10)
                if response.status_code == 200:
                    ip_list = response.text.strip().split('\r\n')
                    for ip in ip_list[:limit]:
                        if ':' in ip:
                            proxies.append({
                                'http': f'http://{ip}',
                                'https': f'http://{ip}'
                            })
            
            self.logger.info(f"Found {len(proxies)} free proxies")
            
        except Exception as e:
            self.logger.error(f"Error fetching free proxies: {str(e)}")
        
        return proxies
    
    def refresh_proxies(self, force: bool = False) -> None:
        """
        Refresh the proxy list by fetching new free proxies
        """
        if force or len(self.proxies) < 5:
            # If we have custom proxies, prioritize them
            if self.custom_proxies:
                self.proxies = []
                for proxy in self.custom_proxies:
                    # Handle both formats: ip:port or ip:port:username:password
                    parts = proxy.split(':')
                    if len(parts) == 2:  # ip:port
                        self.proxies.append({
                            'http': f'http://{proxy}',
                            'https': f'http://{proxy}'
                        })
                    elif len(parts) == 4:  # ip:port:username:password
                        ip, port, username, password = parts
                        self.proxies.append({
                            'http': f'http://{username}:{password}@{ip}:{port}',
                            'https': f'http://{username}:{password}@{ip}:{port}'
                        })
                
                self.logger.info(f"Using {len(self.proxies)} custom proxies")
            else:
                # No custom proxies, get free proxies
                self.proxies = self.get_free_proxies(limit=20)
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get the next proxy from the rotation
        """
        if not self.proxies:
            self.refresh_proxies()
            
        if not self.proxies:
            # Still no proxies available
            self.logger.warning("No proxies available")
            return None
        
        # Round-robin selection with random component to avoid predictability
        if random.random() < 0.3:  # 30% chance of picking random proxy
            proxy = random.choice(self.proxies)
        else:
            # Otherwise use round-robin
            self.last_used_index = (self.last_used_index + 1) % len(self.proxies)
            proxy = self.proxies[self.last_used_index]
        
        return proxy
    
    def remove_proxy(self, proxy: Dict[str, str]) -> None:
        """
        Remove a proxy from the list (e.g., if it's not working)
        """
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.logger.info(f"Removed failing proxy, {len(self.proxies)} proxies remaining")
            
            # Refresh if too few proxies remain
            if len(self.proxies) < 3:
                self.refresh_proxies()

# Create a global instance
proxy_manager = ProxyManager()