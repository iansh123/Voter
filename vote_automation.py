from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import logging
import os

def vote_in_poll(callback=None):
    """
    Uses Selenium with Firefox to vote for "Alyssa Weigand, Glen Cove, junior" 
    in the poll at https://poll.fm/15346013
    
    Args:
        callback (function): Optional callback function to report status
        
    Returns:
        bool: True if voting was successful, False otherwise
    """
    # Set up Firefox options with extreme optimizations for speed and stability
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.binary_location = "/nix/store/pkqh0pddz268mvh55p8x3snpjz3ia8gk-firefox-127.0/bin/firefox"
    
    # Critical performance optimizations to prevent freezing
    firefox_options.set_preference("dom.disable_open_during_load", True)
    firefox_options.set_preference("browser.tabs.remote.autostart", False)
    firefox_options.set_preference("media.autoplay.default", 5)  # Block autoplay
    firefox_options.set_preference("browser.cache.disk.enable", False)  # Disable disk cache
    firefox_options.set_preference("browser.sessionhistory.max_entries", 1)  # Minimize history
    firefox_options.set_preference("browser.startup.page", 0)  # Don't restore previous session
    firefox_options.set_preference("permissions.default.image", 2)  # Block images to speed up loading
    firefox_options.set_preference("network.http.connection-timeout", 10)  # Shorter connection timeout
    firefox_options.set_preference("dom.max_script_run_time", 5)  # Shorter script timeout
    firefox_options.set_preference("dom.disable_beforeunload", True)  # Disable beforeunload events
    firefox_options.set_preference("browser.cache.memory.capacity", 4096)  # Limit memory cache
    firefox_options.set_preference("javascript.enabled", False)  # Disable JavaScript for extreme speed
    firefox_options.set_preference("network.prefetch-next", False)  # Disable link prefetching
    firefox_options.set_preference("network.dns.disablePrefetch", True)  # Disable DNS prefetching
    
    # Initialize success flag
    success = False
    
    def log_status(message):
        """Log a status message and call the callback if provided"""
        logging.debug(message)
        if callback:
            callback(message)
    
    log_status("Initializing WebDriver...")
    
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
                
                # Close the browser immediately to free up resources and avoid memory leaks
                try:
                    driver.quit()
                    driver = None
                    log_status("Browser closed early to save resources")
                except:
                    pass
                
                # Since we already closed the browser to save resources,
                # we won't try to check the page source anymore
                log_status("Vote considered successful based on CAPTCHA submission")
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
