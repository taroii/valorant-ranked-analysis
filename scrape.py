# Import dependencies
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
from clean_label import clean_label
import random
import argparse
from tqdm import tqdm
import logging


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()

def parse_args():
    parser = argparse.ArgumentParser(description="Scrape VALORANT stats from tracker.gg")
    parser.add_argument(
        "--input_csv", 
        type=str, 
        required=False,
        default="top_50_players_per_region.csv", 
        help="Path to CSV file containing player usernames, tags, and regions"
    )
    parser.add_argument(
        "--output_csv", 
        type=str,
        default="scraped_player_stats.csv",
        help="Where to save the scraped data"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode"
    )
    return parser.parse_args()

def simulate_mouse_movement(driver):
    try:
        # Move over the body or a known element (like a header)
        body = driver.find_element(By.TAG_NAME, "body")
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(body, random.randint(50, 300), random.randint(50, 300)).perform()
        time.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        print("Mouse movement failed:", e)

def simulate_scroll(driver):
    try:
        # Scroll down slowly, like a user reading
        scroll_amounts = [200, 400, 600, 800, 1000]
        for y in scroll_amounts:
            driver.execute_script(f"window.scrollTo(0, {y});")
            time.sleep(random.uniform(0.5, 1.2))
    except Exception as e:
        print("Scroll simulation failed:", e)

def wait_for_profile_ready(driver, timeout=30):
    """
    Waits for the profile data to load or times out after `timeout` seconds.
    Returns True if ready, False if still compiling.
    """
    try:
        # Wait until at least one stat block is visible (which means page is loaded)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "stat"))
        )

        # Simulate human activity
        time.sleep(random.uniform(0.5, 1.0))
        simulate_mouse_movement(driver)
        simulate_scroll(driver)

        # Check for "Compiling profile data"
        if "Compiling profile data" in driver.page_source:
            return False

        return True

    except TimeoutException:
        return False

def wait_and_click_show_more(driver):
    try:
        # Wait up to 15 sec for the button to be present and clickable (should already be present but just in case)
        show_more_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Show More")]'))
        )

        # Human-like behavior before clicking
        simulate_scroll(driver)
        simulate_mouse_movement(driver)

        # Click with a small offset to look less bot-like
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(show_more_button, random.randint(-5, 5), random.randint(-3, 3)).pause(random.uniform(0.2, 0.5)).click().perform()

        log.info("Clicked Show More!")
        return True

    except Exception as e:
        log.warning(f"Couldn't find or click 'Show More' button: {e}")
        return False

def scrape(username, tag, region, driver):
    """
    Scrapes all data from tracker.gg for a player and returns stats dict.

    args:
     - username: string of player's IGN username
     - tag: string of player's IGN tag 
     - region: string of player's region
     - driver: active webdriver for selenium navigation

    returns:
     - stats: dictionary containing all stats from designated player
    """

    # Remove spaces from username
    safe_username = username.replace(" ", "_")

    # Go to player's page
    url = f"https://tracker.gg/valorant/profile/riot/{safe_username}%23{tag}/overview?platform=pc&playlist=competitive&season=dcde7346-4085-de4f-c463-2489ed47983b"
    driver.get(url)
    if not wait_for_profile_ready(driver, timeout=30):
        log.warning(f"{username}#{tag} page is not ready (Compiling...) or timed out")
        return None

    # Initialize stats dictionary
    stats = {
        "IGN":f"{username}#{tag}",
        #"IGN":username + "#" + tag,
        "region":region
    }

    # Get RR value
    try:
        stat_blocks = driver.find_elements(By.CLASS_NAME, "stat")
        for block in stat_blocks:
            try:
                sup = block.find_element(By.TAG_NAME, "sup").text.strip()
                if sup == "RR":
                    rr_value = block.find_element(By.CLASS_NAME, "stat__value").text.strip().replace("RR", "").strip()  # remove the RR
                    if rr_value.isdigit():
                        stats["rank_rating"] = int(rr_value)
                    else: 
                        stats["rank_rating"] = rr_value
                    break  # found it!
            except:
                continue
    except Exception as e:
        log.error("Couldn't find rank info:", e)
        return None # Rank info did not load

    # Click "Show More" button
    show_more_click = wait_and_click_show_more(driver)
    if not show_more_click:
        return None  # "Show More" button did not load 
    # try:
    #     show_more_button = WebDriverWait(driver, 10).until(
    #         EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Show More")]'))
    #     )
    #     actions = ActionChains(driver)
    #     actions.move_to_element(show_more_button).pause(random.uniform(0.3, 0.8)).click().perform()
    #     # log.info("Clicked Show More!")
    # except Exception as e:
    #     log.error("Couldn't find or click the Show More button:", e)

    # Collect stats
    try:
        # Wait for the full drawer container to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "drawer__content-stats"))
        )
        time.sleep(1.5)  # allow drawer animation to complete fully

        # Find drawer stat container
        drawer_stats_container = driver.find_element(By.CLASS_NAME, "drawer__content-stats")
        stat_sections = drawer_stats_container.find_elements(By.XPATH, './/div[contains(@class, "bg-surface-1")]')

        for section in stat_sections:
            # Step 1: Grab the header label
            try:
                header_divs = section.find_elements(By.XPATH, './/div[contains(@class, "font-medium") and contains(@class, "text-20")]')
                category = header_divs[0].text.strip() if header_divs else "Uncategorized"
                if not category:
                    category = "Uncategorized"
            except Exception as e:
                log.warning(f"Couldn't extract section title: {e}")
                category = "Uncategorized"

            # Step 2: Grab all stat blocks in the section
            stat_blocks = section.find_elements(By.XPATH, './/div[contains(@class, "stat flex")]')

            for block in stat_blocks:
                try:
                    label_elem = block.find_element(By.CLASS_NAME, "font-normal")
                    value_elem = block.find_element(By.CLASS_NAME, "font-medium")

                    label = label_elem.text.strip()
                    value = value_elem.text.strip()

                    if not label:
                        continue  # skip empty labels

                    label_clean = clean_label(label)
                    full_label = f"{category}_{label_clean}"
                    stats[full_label] = value

                except Exception as e:
                    log.warning(f"Skipping stat in {category}: {e}")
    except Exception as e:
        log.warning(f"Failed to parse drawer stats: {e}")

    # try:
    #     # Wait for the drawer to appear
    #     WebDriverWait(driver, 10).until(
    #         EC.presence_of_element_located((By.CLASS_NAME, "drawer__content-stats"))
    #     )

    #     # Find the container that holds all stat sections
    #     drawer_stats_container = driver.find_element(By.CLASS_NAME, "drawer__content-stats")

    #     # Get all stat sections inside the drawer
    #     stat_sections = drawer_stats_container.find_elements(By.XPATH, './/div[contains(@class, "bg-surface-1")]')

    #     for section in stat_sections:
    #         # Try to extract the category label
    #         try:
    #             title_div = section.find_element(By.XPATH, './/div[contains(@class, "font-medium") and contains(@class, "text-20")]')
    #             category = title_div.text.strip()
    #         except:
    #             category = "Uncategorized"

    #         # Get each stat block inside the section
    #         stat_blocks = section.find_elements(By.XPATH, './/div[contains(@class, "stat flex")]')

    #         for block in stat_blocks:
    #             try:
    #                 label = block.find_element(By.CLASS_NAME, "font-normal").text.strip()
    #                 value = block.find_element(By.CLASS_NAME, "font-medium").text.strip()

    #                 label_clean = clean_label(label)
    #                 full_label = f"{category}_{label_clean}"
    #                 stats[full_label] = value
    #             except Exception as e:
    #                 log.warning(f"Skipping stat in {category}: {e}")

    # except Exception as e:
    #     log.warning(f"Failed to locate or parse drawer stats: {e}")
    
    # # Find all stat sections (Combat, Game, Attack, Defense, Uncategorized)
    # stat_sections = driver.find_elements(By.XPATH, '//div[contains(@class, "bg-surface-1 flex flex-col gap-px")]')

    # # Collect data from each stat section
    # for section in stat_sections:
    #     try:
    #         # Get section title
    #         category = section.find_element(By.XPATH, './/div[contains(@class, "font-medium text-20")]').text.strip()
    #     except:
    #         category = "Uncategorized"

    #     stat_blocks = section.find_elements(By.XPATH, './/div[contains(@class, "stat flex")]')

    #     for block in stat_blocks:
    #         try:
    #             label = block.find_element(By.CLASS_NAME, "font-normal").text.strip()
    #             value = block.find_element(By.CLASS_NAME, "font-medium").text.strip()
    #             # Prefix the stat label with the category
    #             label_clean = clean_label(label)
    #             full_label = f"{category}_{label_clean}"
    #             stats[full_label] = value
    #         except Exception as e:
    #             log.warning(f"Skipping stat in {category}: {e}")

    # if not stats or len(stats) <= 2:  # Only has IGN and region
    #     log.warning(f"Failed to scrape: {username}#{tag}")
    #     return None
    
    return stats

if __name__ == "__main__":
    args = parse_args()
    input_csv_path = args.input_csv

    # Load player DataFrame from the CSV
    player_df = pd.read_csv(input_csv_path)

    # Load undetected Chrome driver
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if args.headless:
        options.add_argument("--headless=new")
    driver = uc.Chrome(options=options)

    results = []
    batch_size = 25
    cooldown_minutes = 5
    for i, row in enumerate(tqdm(player_df.itertuples(), total=len(player_df))):
        try:
            player_stats = scrape(row.username, row.tag, row.region, driver)
            if player_stats:
                results.append(player_stats)
        except Exception as e:
            log.warning(f"Error scraping {row.username}#{row.tag}: {e}")
        
        # Sleep between requests AND cooldown after every batch
        time.sleep(random.uniform(10, 20))
        if (i + 1) % batch_size == 0:
            pd.DataFrame(results).to_csv(args.output_csv, index=False)
            log.info(f"Batch {i+1} saved. Cooling down for {cooldown_minutes} minutes.")
            time.sleep(cooldown_minutes * 60)


    # for i, row in tqdm(player_df.iterrows(), total=len(player_df)):
    #     if i % 10 == 0:
    #         time.sleep(random.uniform(20, 30))
    #     max_retries = 2
    #     for attempt in range(max_retries):
    #         try:
    #             player_stats = scrape(row["username"], row["tag"], row["region"], driver)
    #             if player_stats:
    #                 results.append(player_stats)
    #             break
    #         except Exception as e:
    #             print(f"Retrying {row['username']}#{row['tag']} (attempt {attempt+1}) due to error: {e}")
    #             time.sleep(random.uniform(2, 4))

    final_df = pd.DataFrame(results)
    final_df.to_csv(args.output_csv, index=False)
    log.info("Sample row:")
    log.info(final_df.iloc[0].to_dict())
    log.info(f"Saved {len(final_df)} players to {args.output_csv}")

    driver.quit()