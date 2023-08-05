import pandas as pd
from playwright.sync_api import sync_playwright
from gcal import get_creds, get_calendar
import ezpass
import os


def main():

    month = int(input("\nWhich Month (0-12)? "))

    # Get work days from google calendar
    service = get_creds()
    work_days = get_calendar(service, month)

    # Scrape the tolls from EZ-Pass
    tolls_html = get_tolls()

    tolls = make_dataframe(tolls_html, month)
    query_tolls(tolls, work_days)


def get_tolls():

    # use playwright to log in and download the statements table
    with sync_playwright() as p:

        print("\nLaunching browser.")
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        page.goto("https://www.ezpassnh.com")

        print("-Logging into EZ-Pass.")
        page.locator('a[class="js-btnLogin"]').click()
        page.fill("input#loginReturnDialog", ezpass.username)
        page.fill("input#passwordReturnDialog", ezpass.password)
        page.click('button[id="btnReturnLogin"]')

        print("-Loading statement page.")
        page.goto("https://www.ezpassnh.com/account/statement-and-activity/statement")
        #page.locator('button[id="btnFiler"]').click()

        print("-Scraping table.")
        tolls_html = page.inner_html(".ezpass-container-table")
        browser.close()
        print("Browser closed.\n")

    return tolls_html


def make_dataframe(tolls_html, month):

    # read in the scraped html
    tolls = pd.read_html(tolls_html)

    # tolls[0] pulls the table out of the list object
    tolls = tolls[0][["Transaction Date/Time", "Description", "Amount"]]

    # shorten the column names
    tolls = tolls.rename(
        columns={
            "Transaction Date/Time": "Date",
            "Description": "Location",
            "Amount": "Amount",
        }
    )

    # convert date to a datetime object
    tolls["Date"] = pd.to_datetime(tolls["Date"])

    # strip the extra text and leave the location name
    tolls["Location"] = tolls["Location"].str[8:]

    # remove text and convert the number to a float
    tolls["Amount"] = tolls["Amount"].str[3:].astype(float)

    # Get the record for a certain month
    tolls = tolls[tolls["Date"].dt.month == month]

    # remove rows where the amount == 0
    tolls = tolls[tolls["Amount"] > 0]

    # sort dataframe by date
    tolls = tolls.sort_values(by="Date")

    # convert the date to a formatted string
    tolls["Date"] = tolls["Date"].dt.strftime("%Y-%m-%d")

    return tolls


def query_tolls(tolls, work_days):

    # find all toll that were paid on a work day
    tolls = tolls.query("Date in @work_days")

    # reset the index to begin at 0
    tolls = tolls.reset_index(drop=True)

    # add a 'Total' row with the sum of the amount column
    tolls.loc[len(tolls.index)] = ["", "Total", tolls["Amount"].sum()]

    # save as an excel file
    os.chdir(r"/Users/dougmartin/Desktop")
    tolls.to_excel("tolls.xlsx", index=False)

    # print to console
    print(tolls.to_string(index=False))
    
    print()


if __name__ == "__main__":
    main()
