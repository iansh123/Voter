from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os

def vote_in_poll(times=1):
    """
    Uses Selenium with Firefox to vote for "Alyssa Weigand, Glen Cove, junior" 
    in the poll at https://poll.fm/15346013
    
    Args:
        times (int): Number of times to vote
    """
    # Set up Firefox options
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.binary_location = "/nix/store/pkqh0pddz268mvh55p8x3snpjz3ia8gk-firefox-127.0/bin/firefox"
    
    # Uncomment the line below if you want to run in headless mode (no browser window)
    # firefox_options.add_argument("--headless")
    
    for i in range(times):
        print(f"Starting vote attempt {i+1}...")
        
        # Set up the driver
        driver = webdriver.Firefox(
            service=Service("/nix/store/kxz4y57xlv70567x1zbvarmn5ry2asx4-geckodriver-0.34.0/bin/geckodriver"),
            options=firefox_options
        )
        
        try:
            # Navigate to the poll
            driver.get("https://poll.fm/15346013")
            
            # Wait for the poll to load
            wait = WebDriverWait(driver, 10)
            
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
                print("Selected 'Alyssa Weigand, Glen Cove, junior'")
                
                # Find and click the vote button
                vote_button = wait.until(EC.element_to_be_clickable((By.ID, "pd-vote-button15346013")))
                driver.execute_script("arguments[0].click();", vote_button)
                print(f"Vote {i+1} submitted!")
                time.sleep(2)
                # Wait to see the results or confirmation
                element = driver.find_element(By.XPATH, "/html/body/form/div[1]/span/p")
                print("Element Text:", element.text[:-2])
                answer = element.text[:-2]
                mathanswer = eval(answer)
                answerdriver = driver.find_element(By.ID, "answer_15346013")
                answerdriver.send_keys(mathanswer)
                print(mathanswer)
                time.sleep(1)
                vote_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "button-lrg")))
                driver.execute_script("arguments[0].click();", vote_button)
                time.sleep(1)
                
                # Check if there's a "Return To Poll" button which indicates successful voting
                try:
                    driver.find_element(By.CSS_SELECTOR, "a.pds-return-poll")
                    print(f"Vote {i+1} confirmed successful!")
                except:
                    print(f"Could not confirm if vote {i+1} was counted")
                
            else:
                print("Could not find the option for Alyssa Weigand, Glen Cove, junior")
        
        except Exception as e:
            print(f"Error during voting attempt {i+1}: {str(e)}")
            
        finally:
            # Close the browser
            driver.quit()
            
            # Add a random delay between votes
            if i < times - 1:  # No need to wait after the last vote
                delay = random.uniform(5, 10)
                print(f"Waiting {delay:.2f} seconds before next vote...")
                time.sleep(delay)
    
    print("All voting attempts completed!")

if __name__ == "__main__":
    import sys
    try:
        # Check if a command line argument is provided
        if len(sys.argv) > 1:
            num_votes = int(sys.argv[1])
            print(f"Running with {num_votes} votes from command line argument")
        else:
            # Fall back to input if no argument is provided
            num_votes = int(input("How many times would you like to vote? "))
        
        vote_in_poll(num_votes)
    except ValueError:
        print("Please enter a valid number.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")