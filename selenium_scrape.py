import os
import time
import requests
from io import BytesIO
from dotenv import load_dotenv
import boto3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Load environment variables
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")

BASE_URL = "https://investor.nvidia.com/financial-info/quarterly-results/default.aspx"


def upload_pdf_to_s3(pdf_file, s3_path):
    """
    Uploads a PDF file (BytesIO) to S3 under the given key.
    """
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    s3.upload_fileobj(pdf_file, AWS_BUCKET, s3_path)
    print(f"✅ Uploaded to s3://{AWS_BUCKET}/{s3_path}")


def expand_quarter(driver, quarter_button_id):
    """
    Expands a quarter if it's collapsed.
    """
    try:
        quarter_button = driver.find_element(By.ID, quarter_button_id)
        
        # Check if already expanded
        if quarter_button.get_attribute("aria-expanded") == "false":
            driver.execute_script("arguments[0].scrollIntoView();", quarter_button)
            quarter_button.click()
            time.sleep(3)  # Allow the content to load
            print(f"✅ Expanded {quarter_button.text}")

    except Exception as e:
        print(f"⚠️ Could not expand {quarter_button_id}: {e}")


def scrape_nvidia_reports_for_year(year):
    """
    Scrapes NVIDIA financial reports (10-K and 10-Q) for a specific year.
    Expands all quarters (Q4, Q3, Q2, Q1) and downloads PDFs.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(BASE_URL)
        print(f"\n🌐 Opened {BASE_URL} for year {year}")

        wait = WebDriverWait(driver, 15)

        # Wait for the dropdown to load
        dropdown_element = wait.until(
            EC.presence_of_element_located((By.ID, "_ctrl0_ctl75_selectEvergreenFinancialAccordionYear"))
        )

        dropdown = Select(dropdown_element)
        available_years = [option.text.strip() for option in dropdown.options]
        print(f"📅 Available Years: {available_years}")

        if str(year) not in available_years:
            print(f"⚠️ Year {year} not found in dropdown. Skipping...")
            return

        dropdown.select_by_visible_text(str(year))
        print(f"✅ Selected year: {year}")

        time.sleep(3)  # Wait for content to load

        # Define the correct expand button IDs per year
        quarter_buttons = {
            "Fourth Quarter": "tab11",
            "Third Quarter": "tab12",
            "Second Quarter": "tab13",
            "First Quarter": "tab14"
        }

        found_docs = []
        for quarter_text, button_id in quarter_buttons.items():
            try:
                print(f"🔄 Processing {quarter_text} for {year}...")

                # Expand the quarter section
                expand_quarter(driver, button_id)

                # Find all PDF links inside the expanded quarter
                pdf_links = driver.find_elements(By.CSS_SELECTOR, "a.evergreen-financial-accordion-attachment-PDF")

                for link in pdf_links:
                    text = link.text.strip()
                    href = link.get_attribute("href")
                    if not href or not href.endswith(".pdf"):
                        continue
                    if "10-K" not in text and "10-Q" not in text:
                        continue

                    # Map quarter names to Q1-Q4 format
                    quarter_map = {
                        "Fourth Quarter": "Q4",
                        "Third Quarter": "Q3",
                        "Second Quarter": "Q2",
                        "First Quarter": "Q1"
                    }
                    
                    quarter = quarter_map[quarter_text]
                    print(f"⬇️ Downloading {text} ({quarter}) for {year}")

                    try:
                        response = requests.get(href)
                        if response.status_code == 200:
                            s3_key = f"Raw_PDFs/{year}/{quarter}.pdf"
                            upload_pdf_to_s3(BytesIO(response.content), s3_key)
                            found_docs.append(quarter)
                        else:
                            print(f"⚠️ Failed to fetch PDF: {href}")
                    except Exception as e:
                        print(f"❌ Error downloading {href}: {e}")

                time.sleep(2)  # Small delay before moving to the next quarter

            except Exception as e:
                print(f"⚠️ Skipping {quarter_text} due to error: {e}")
                continue

        print(f"📄 Done with {year}. Uploaded {len(found_docs)} PDFs: {found_docs}")

    finally:
        driver.quit()


if __name__ == "__main__":
    # Scrape for the last 5 years (2025 → 2021)
    for yr in range(2025, 2020, -1):
        scrape_nvidia_reports_for_year(yr)
