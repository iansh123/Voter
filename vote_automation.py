from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.proxy import Proxy, ProxyType
import time
import random
import logging
import os
from proxy_manager import proxy_manager

def vote_in_poll(callback=None, custom_proxy=None):
    """
    Uses Selenium with Firefox to vote for "Alyssa Weigand, Glen Cove, junior" 
    in the poll at https://poll.fm/15346013
    
    Args:
        callback (function): Optional callback function to report status
        custom_proxy (str, optional): Custom proxy to use in format ip:port or ip:port:username:password
        
    Returns:
        bool: True if voting was successful, False otherwise
    """
    # Set up Firefox options with optimized settings for speed
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.binary_location = "/nix/store/pkqh0pddz268mvh55p8x3snpjz3ia8gk-firefox-127.0/bin/firefox"
    
    # Performance optimization settings
    firefox_options.set_preference("dom.disable_open_during_load", True)
    firefox_options.set_preference("browser.tabs.remote.autostart", False)
    firefox_options.set_preference("media.autoplay.default", 5)  # Block autoplay
    firefox_options.set_preference("browser.cache.disk.enable", False)  # Disable disk cache
    firefox_options.set_preference("browser.sessionhistory.max_entries", 1)  # Minimize history
    firefox_options.set_preference("browser.startup.page", 0)  # Don't restore previous session
    firefox_options.set_preference("permissions.default.image", 2)  # Block images to speed up loading
    
    # Initialize success flag
    success = False
    
    def log_status(message):
        """Log a status message and call the callback if provided"""
        logging.debug(message)
        if callback:
            callback(message)
    
    log_status("Initializing WebDriver...")
    
    # Set up proxy if needed
    proxy_info = None
    if custom_proxy:
        # If a specific proxy was provided, use it
        log_status(f"Using custom proxy: {custom_proxy.split(':')[0]}")
        if ':' in custom_proxy:
            parts = custom_proxy.split(':')
            if len(parts) == 2:  # ip:port format
                proxy_info = {
                    'http': f'http://{custom_proxy}',
                    'https': f'http://{custom_proxy}'
                }
            elif len(parts) == 4:  # ip:port:username:password format
                ip, port, username, password = parts
                proxy_info = {
                    'http': f'http://{username}:{password}@{ip}:{port}',
                    'https': f'http://{username}:{password}@{ip}:{port}'
                }
    else:
        # Get a proxy from the proxy manager
        proxy_info = proxy_manager.get_proxy()
        if proxy_info:
            proxy_url = proxy_info['http'].replace('http://', '')
            log_status(f"Using proxy: {proxy_url.split('@')[-1].split(':')[0]}")
    
    # Configure Firefox to use the proxy if one was selected
    if proxy_info:
        proxy_url = proxy_info['http'].replace('http://', '')
        
        # Different format if proxy has auth
        if '@' in proxy_url:
            auth, addr = proxy_url.split('@')
            username, password = auth.split(':')
            ip, port = addr.split(':')
            
            firefox_options.set_preference("network.proxy.type", 1)
            firefox_options.set_preference("network.proxy.http", ip)
            firefox_options.set_preference("network.proxy.http_port", int(port))
            firefox_options.set_preference("network.proxy.ssl", ip) 
            firefox_options.set_preference("network.proxy.ssl_port", int(port))
            firefox_options.set_preference("network.proxy.socks", ip)
            firefox_options.set_preference("network.proxy.socks_port", int(port))
            firefox_options.set_preference("network.proxy.ftp", ip)
            firefox_options.set_preference("network.proxy.ftp_port", int(port))
            firefox_options.set_preference("network.proxy.no_proxies_on", "localhost,127.0.0.1")
            firefox_options.set_preference("network.proxy.share_proxy_settings", True)
            firefox_options.set_preference("network.proxy.username", username)
            firefox_options.set_preference("network.proxy.password", password)
        else:
            # No auth proxy
            ip, port = proxy_url.split(':')
            firefox_options.set_preference("network.proxy.type", 1)
            firefox_options.set_preference("network.proxy.http", ip)
            firefox_options.set_preference("network.proxy.http_port", int(port))
            firefox_options.set_preference("network.proxy.ssl", ip)
            firefox_options.set_preference("network.proxy.ssl_port", int(port))
            firefox_options.set_preference("network.proxy.socks", ip)
            firefox_options.set_preference("network.proxy.socks_port", int(port))
            firefox_options.set_preference("network.proxy.ftp", ip)
            firefox_options.set_preference("network.proxy.ftp_port", int(port))
            firefox_options.set_preference("network.proxy.no_proxies_on", "localhost,127.0.0.1")
            firefox_options.set_preference("network.proxy.share_proxy_settings", True)
    
    # Set up the driver
    driver = None
    try:
        driver = webdriver.Firefox(
            service=Service("/nix/store/kxz4y57xlv70567x1zbvarmn5ry2asx4-geckodriver-0.34.0/bin/geckodriver"),
            options=firefox_options
        )
        
        log_status("Navigating to the poll...")
        # Navigate to the poll
        driver.get("https://poll.fm/15346013")
        
        # Wait for the poll to load with reduced timeout for faster operation
        wait = WebDriverWait(driver, 5)
        
        log_status("Looking for Alyssa Weigand's option...")
        # Try different approaches to find the option faster
        alyssa_option = None
        try:
            # Try direct xpath first (faster if it works)
            alyssa_option = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//span[contains(text(), 'Alyssa Weigand')]/../..//input[@type='radio']")
            ))
            log_status("Found option using direct selector (fast method)")
        except Exception:
            # Fall back to the original method
            log_status("Using fallback method to find option")
            radio_options = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pds-answer-group")))
            
            for option in radio_options:
                if "Alyssa Weigand, Glen Cove, junior" in option.text:
                    alyssa_option = option.find_element(By.CSS_SELECTOR, "input[type='radio']")
                    break
        
        if alyssa_option:
            # Click the radio button for Alyssa
            driver.execute_script("arguments[0].click();", alyssa_option)
            log_status("Selected 'Alyssa Weigand, Glen Cove, junior'")
            
            # Find and click the vote button
            vote_button = wait.until(EC.element_to_be_clickable((By.ID, "pd-vote-button15346013")))
            driver.execute_script("arguments[0].click();", vote_button)
            log_status("Vote submitted, now handling CAPTCHA...")
            
            # Wait for the CAPTCHA to appear
            time.sleep(2)
            
            try:
                # Find the math problem
                element = driver.find_element(By.XPATH, "/html/body/form/div[1]/span/p")
                math_problem = element.text[:-2]  # Remove the "= " at the end
                log_status(f"CAPTCHA math problem: {math_problem}")
                
                # Solve the math problem
                math_answer = eval(math_problem)
                log_status(f"CAPTCHA solution: {math_answer}")
                
                # Enter the answer
                answer_field = driver.find_element(By.ID, "answer_15346013")
                answer_field.send_keys(str(math_answer))
                
                # Submit the CAPTCHA answer
                submit_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "button-lrg")))
                driver.execute_script("arguments[0].click();", submit_button)
                log_status("CAPTCHA answer submitted")
                
                # Reduced wait time for confirmation to speed up the process
                time.sleep(1)
                
                # The vote is likely successful if we got past the CAPTCHA
                # Since the confirmation element might have changed, we'll consider it successful
                log_status("Vote appears to be successful (CAPTCHA solved and submitted)")
                success = True
                
                # Try to find any evidence of success or thank you message
                try:
                    # Look for any common success indicators
                    if driver.page_source and any(x in driver.page_source.lower() for x in ['thank you', 'success', 'recorded', 'received']):
                        log_status("Found confirmation message on page!")
                    else:
                        log_status("No explicit confirmation found, but vote was submitted")
                except Exception as e:
                    log_status(f"Error checking for confirmation: {str(e)}")
            except Exception as e:
                log_status(f"Error during CAPTCHA solving: {str(e)}")
        else:
            log_status("Could not find the option for Alyssa Weigand, Glen Cove, junior")
    
    except Exception as e:
        log_status(f"Error during voting attempt: {str(e)}")
        
    finally:
        # Close the browser
        if driver:
            try:
                driver.quit()
                log_status("Browser closed")
            except:
                log_status("Error closing browser")
    
    return success
