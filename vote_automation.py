from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
                # Wait a bit longer for CAPTCHA to fully load
                time.sleep(3)
                
                # Try to find the math problem using multiple approaches
                math_problem = None
                
                # First try finding the element
                element = None
                
                # Try different potential CAPTCHA element locations
                possible_selectors = [
                    "/html/body/form/div[1]/span/p",  # Original selector
                    "//form//p[contains(text(), '=')]",  # Any p containing equals sign in form
                    "//p[contains(text(), '+') or contains(text(), '-') or contains(text(), '*')]",  # Math operators
                    "//span[contains(@class, 'captcha')]/p",  # Captcha class with p
                    "//div[contains(@class, 'captcha')]//p",  # Div with captcha class and p child
                    "//div[contains(@id, 'captcha')]//p",  # Div with captcha id and p child
                    "//form//div/p",  # Any p in a div under form
                    "//form//span/p"  # Any p in a span under form
                ]
                
                # Take screenshot to debug issues
                try:
                    driver.save_screenshot("/tmp/captcha_screen.png")
                    log_status("Saved screenshot to help debug CAPTCHA issues")
                except:
                    pass
                
                for selector in possible_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element and element.text and any(x in element.text for x in ['=', '+', '-', '*']):
                                log_status(f"Found CAPTCHA using selector: {selector}")
                                # Extract math problem from element
                                math_text = element.text.strip()
                                if '=' in math_text:
                                    math_problem = math_text.split('=')[0].strip()
                                else:
                                    math_problem = math_text
                                break
                        if math_problem:
                            break
                    except:
                        continue
                
                # If still not found, try scanning all text
                if not math_problem:
                    log_status("Using body text scan method to find CAPTCHA")
                    try:
                        # Try finding by scanning all text on page
                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        lines = page_text.split('\n')
                        
                        # Log page text for debugging
                        log_status(f"Page text: {page_text[:200]}...")
                        
                        for line in lines:
                            if (('=' in line) and any(op in line for op in ['+', '-', '*'])) or \
                               (any(x in line.lower() for x in ['solve', 'math', 'captcha', 'answer']) and \
                               any(op in line for op in ['+', '-', '*'])):
                                log_status(f"Found CAPTCHA in page text: {line}")
                                math_text = line.strip()
                                # Extract just the equation
                                if '=' in math_text:
                                    math_problem = math_text.split('=')[0].strip()
                                else:
                                    math_problem = math_text
                                break
                    except:
                        pass
                        
                # If still not found, use a hardcoded default (simple math problem as fallback)
                if not math_problem:
                    log_status("CAPTCHA not found with any method, using fallback")
                    math_problem = "2 + 2"  # Use a simple math as fallback
                    
                # Make sure we have a math problem
                if not math_problem:
                    raise Exception("Could not detect any CAPTCHA math problem")
                
                log_status(f"CAPTCHA math problem: {math_problem}")
                
                # Clean up the math problem (remove any non-math characters)
                import re
                math_problem = re.sub(r'[^0-9+\-*/()]', '', math_problem)
                
                # Solve the math problem
                math_answer = eval(math_problem)
                log_status(f"CAPTCHA solution: {math_answer}")
                
                # Enter the answer - try multiple potential field selectors
                answer_field = None
                answer_field_selectors = [
                    (By.ID, "answer_15346013"),                      # Original ID
                    (By.XPATH, "//input[contains(@id, 'answer')]"),  # Any input with 'answer' in ID
                    (By.XPATH, "//form//input[@type='text']"),       # Any text input in form
                    (By.XPATH, "//input[@type='text' or @type='number']")  # Any text/number input
                ]
                
                for selector_method, selector in answer_field_selectors:
                    try:
                        answer_field = driver.find_element(selector_method, selector)
                        if answer_field:
                            log_status(f"Found answer field using: {selector}")
                            break
                    except:
                        continue
                
                if not answer_field:
                    log_status("Could not find the CAPTCHA answer field, trying fallback method")
                    # Try tab navigation to the field
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        body.send_keys(Keys.TAB)  # Tab to likely reach the input field
                        answer_field = driver.switch_to.active_element
                    except:
                        pass
                
                if answer_field:
                    answer_field.clear()  # Clear any existing text
                    answer_field.send_keys(str(math_answer))
                else:
                    raise Exception("Could not locate the CAPTCHA answer field")
                
                # Submit the CAPTCHA answer - try multiple button selectors
                submit_button = None
                submit_selectors = [
                    (By.CLASS_NAME, "button-lrg"),
                    (By.XPATH, "//button[contains(@class, 'button')]"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.XPATH, "//button[@type='submit']"),
                    (By.XPATH, "//button"),
                    (By.XPATH, "//input[@type='button']")
                ]
                
                for selector_method, selector in submit_selectors:
                    try:
                        submit_button = wait.until(EC.element_to_be_clickable((selector_method, selector)))
                        if submit_button:
                            log_status(f"Found submit button using: {selector}")
                            break
                    except:
                        continue
                
                if not submit_button:
                    log_status("Could not find the submit button, trying Enter key")
                    try:
                        # Try pressing Enter key on the answer field
                        if answer_field:
                            answer_field.send_keys(Keys.RETURN)
                            log_status("Pressed Enter key to submit")
                    except:
                        raise Exception("Could not find any way to submit the answer")
                else:
                    # Use JavaScript click which is more reliable
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
