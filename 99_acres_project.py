"""
99acres.com Property Scraper
----------------------------
Scrapes property listings from 99acres.com based on city and filters.
Exports clean data to Excel.

Author: [Your Name]
GitHub: https://github.com/yourusername
"""

import time
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PropertyScraper:
    def __init__(self, url, timeout=20):
        self.url = url
        self.data = []
        self.driver = self._initialize_driver()
        self.wait = WebDriverWait(self.driver, timeout)

    def _initialize_driver(self):
        # Setup headless Chrome browser
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-http2")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--enable-features=NetworkServiceInProcess")
        chrome_options.add_argument("--disable-features=NetworkService")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver

    def _wait_for_page_fully_load(self):
        # Wait until the document is fully loaded
        title = self.driver.title
        try:
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            print(f"⚠️ Page \"{title}\" did NOT load in time.")
        else:
            print(f"✅ Page \"{title}\" fully loaded.")

    def access_website(self):
        self.driver.get(self.url)
        self._wait_for_page_fully_load()

    def search_properties(self, text):
        # Fill search bar with city name and start search
        try:
            search_bar = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="keyword2"]')))
            search_bar.send_keys(text)
        except:
            print("❌ Failed to locate search bar.")
            return

        try:
            valid_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="0"]')))
            valid_option.click()
        except:
            print("❌ Couldn't select suggested location.")

        try:
            search_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="searchform_search_btn"]')))
            search_button.click()
            self._wait_for_page_fully_load()
        except:
            print("❌ Search button not clickable.")

    def adjust_budget_slider(self, offset):
        # Adjust budget range slider by offset
        try:
            slider = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="budgetLeftFilter_max_node"]')))
            actions = ActionChains(self.driver)
            actions.click_and_hold(slider).move_by_offset(offset, 0).release().perform()
        except:
            print("❌ Couldn't move the budget slider.")

    def apply_filters(self):
        # Click on filters: Verified, Ready to Move, With Photos, With Videos
        try:
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//div[3]/span[2]'))).click()  # Verified
            time.sleep(2)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//div[5]/span[2]'))).click()  # Ready to Move
            time.sleep(2)
        except:
            print("⚠️ Couldn't apply Verified/Ready filters.")

        # Navigate to all filter options
        while True:
            try:
                right_arrow = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//i[contains(@class,'cc__rightArrow')]")))
                right_arrow.click()
                time.sleep(1)
            except:
                break  # No more right arrows

        # Apply final filters
        try:
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//div[6]/span[2]'))).click()  # With Photos
            time.sleep(2)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//div[7]/span[2]'))).click()  # With Videos
            time.sleep(2)
        except:
            print("⚠️ Couldn't apply photo/video filters.")

    def _extract_data(self, row, by, value):
        # Helper function to extract text from element
        try:
            return row.find_element(by, value).text
        except:
            return np.nan

    def scrape_webpage(self):
        # Extract property data from listings on current page
        rows = self.driver.find_elements(By.CLASS_NAME, "tupleNew__contentWrap")
        for row in rows:
            name = self._extract_data(row, By.CLASS_NAME, "tupleNew__headingNrera")
            location = self._extract_data(row, By.CLASS_NAME, "tupleNew__tupleHeadingTopaz")
            price = self._extract_data(row, By.CLASS_NAME, "tupleNew__priceValWrap")

            try:
                elements = row.find_elements(By.CLASS_NAME, "tupleNew__area1Type")
                area, bhk = [ele.text for ele in elements]
            except:
                area, bhk = np.nan, np.nan

            self.data.append({
                "name": name,
                "location": location,
                "price": price,
                "area": area,
                "bhk": bhk
            })

    def navigate_pages_and_extract_data(self):
        # Loop through result pages and scrape all listings
        page_count = 0
        while True:
            page_count += 1
            self.scrape_webpage()

            try:
                next_btn = self.driver.find_element(By.XPATH, "//a[normalize-space()='Next Page >']")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(3)
                next_btn.click()
                time.sleep(6)
            except:
                print(f"✅ Finished scraping {page_count} pages.")
                break

    def clean_and_export_data_in_excel(self, filename):
        # Clean data and export to Excel
        df = (
            pd.DataFrame(self.data)
            .drop_duplicates()
            .apply(lambda col: col.str.strip().str.lower() if col.dtype == "object" else col)
            .assign(
                is_starred=lambda df: df.name.str.contains("\n").astype(int),
                name=lambda df: df.name.str.replace("\n[0-9.]+", "", regex=True).str.strip(),
                location=lambda df: (
                    df.location
                    .str.replace("chennai", "", regex=False)
                    .str.replace(r"\n·\nrera", "", regex=True)
                    .str.replace(r",$", "", regex=True)
                    .str.split("in").str[-1].str.strip()
                ),
                price=lambda df: (
                    df.price.str.replace("₹", "")
                    .apply(lambda val: float(val.replace("lac", "").strip()) if "lac" in val else float(val.replace("cr", "").strip()) * 100)
                ),
                area=lambda df: df.area.str.replace("sqft", "").str.replace(",", "").str.strip().astype(int),
                bhk=lambda df: df.bhk.str.replace("bhk", "").str.strip().astype(int)
            )
            .rename(columns={"price": "price_in_lac", "area": "area_in_sqft"})
            .reset_index(drop=True)
        )

        df.to_excel(f"{filename}.xlsx", index=False)
        print(f"\n📁 Exported data to {filename}.xlsx")

    def run(self, text, offset=-100, filename="properties"):
        # Full pipeline: access site, search, filter, scrape, clean, export
        try:
            self.access_website()
            self.search_properties(text)
            self.adjust_budget_slider(offset)
            self.apply_filters()
            self.navigate_pages_and_extract_data()
            self.clean_and_export_data_in_excel(filename)
        finally:
            time.sleep(3)
            self.driver.quit()


# ▶️ Start scraping process
if __name__ == "__main__":
    scraper = PropertyScraper(url="https://www.99acres.com")
    scraper.run("chennai", -73, "chennai_properties")
