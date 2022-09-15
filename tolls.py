import pandas as pd
from playwright.sync_api import sync_playwright
from gcal import get_creds, get_calendar
import ezpass


def main():

    month = int(input("Which Month (0-12)? "))

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

        print("Launching browser in headless mode...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.ezpassnh.com")

        print("Logging into EZ-Pass...")
        page.locator('a[class="js-btnLogin"]').click()
        page.fill("input#loginReturnDialog", ezpass.username)
        page.fill("input#passwordReturnDialog", ezpass.password)
        page.click('button[id="btnReturnLogin"]')

        print("Loading statement page...")
        page.goto("https://www.ezpassnh.com/account/statement-and-activity/statement")
        page.locator('button[id="btnFiler"]').click()

        print("Scraping table...")
        tolls_html = page.inner_html(".ezpass-container-table")
        browser.close()

    # # save as html
    # with open("tolls.html", "w") as f:
    #     f.write(tolls_html)

    return tolls_html


def make_dataframe(tolls_html, month):

    # read in the scraped html
    tolls = pd.read_html(tolls_html)

    # tolls[0] pulls the table out of the list object
    tolls = tolls[0][["Transaction Date/Time", "Description", "Amount"]]

    # shorten the column names
    tolls = tolls.rename(
        columns={
            "Transaction Date/Time": "date",
            "Description": "location",
            "Amount": "amount",
        }
    )

    # convert date to a datetime object
    tolls["date"] = pd.to_datetime(tolls["date"])

    # strip the extra text and leave the location name
    tolls["location"] = tolls["location"].str[8:]

    # remove text and convert the number to a float
    tolls["amount"] = tolls["amount"].str[3:].astype(float)

    # Get the record for a certain month
    tolls = tolls[tolls["date"].dt.month == month]

    # remove rows where the amount == 0
    tolls = tolls[tolls["amount"] > 0]

    # sort dataframe by date
    tolls = tolls.sort_values(by="date")

    # convert the date to a formatted string
    tolls["date"] = tolls["date"].dt.strftime("%Y-%m-%d")

    return tolls


def query_tolls(tolls, work_days):

    # find all toll that were paid on a work day
    tolls = tolls.query("date in @work_days")

    # reset the index to begin at 0
    tolls = tolls.reset_index(drop=True)

    # add a 'Total' row with the sum of the amount column
    tolls.loc[len(tolls.index)] = ["", "Total", tolls["amount"].sum()]

    # save as an excel file
    tolls.to_excel("tolls.xlsx", index=False)

    # print to console
    print(tolls.to_string(index=False))


if __name__ == "__main__":
    main()
