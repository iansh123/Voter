from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import time
import random
import logging

def vote_in_poll(callback=None):
    """
    Uses Selenium with Firefox to vote for "Alyssa Weigand, Glen Cove, junior" 
    in the poll at https://poll.fm/15346013
    
    Args:
        callback (function): Optional callback function to report status
        
    Returns:
        bool: True if voting was successful, False otherwise
    """
    # Set up Firefox options
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    
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
            service=Service(GeckoDriverManager().install()),
            options=firefox_options
        )
        
        log_status("Navigating to the poll...")
        # Navigate to the poll
        driver.get("https://poll.fm/15346013")
        
        # Wait for the poll to load
        wait = WebDriverWait(driver, 10)
        
        log_status("Looking for Alyssa Weigand's option...")
        # Find all radio button options and look for Alyssa Weigand
        radio_options = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pds-answer-group")))
        
        alyssa_option = None
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
                
                # Wait for confirmation
                time.sleep(2)
                
                # Check if there's a "Return To Poll" button which indicates successful voting
                try:
                    driver.find_element(By.CSS_SELECTOR, "a.pds-return-poll")
                    log_status("Vote confirmed successful!")
                    success = True
                except:
                    log_status("Could not confirm if vote was counted")
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
