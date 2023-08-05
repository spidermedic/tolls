from datetime import datetime, timedelta
import calendar
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    month = int(input("\nWhich Month (0-12)? "))
    service = get_creds()
    work_days = get_calendar(service, month)
    print()
    for day in work_days:
        print(day.date())
    print()


def get_creds():

    # Check to see if there is a token file and load the credentials
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        print("\nToken found.")
    else:
        creds = None

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        # Write the token to a file
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            print("\nToken saved.")     


    return build("calendar", "v3", credentials=creds)


def get_calendar(service, month):

    print("\nGetting worked days from Google calendar.")

    work_days = []

    first_day = datetime(2023, month, 1).isoformat() + "Z"
    last_day = datetime(2023, month, calendar.monthrange(2023, month)[1]) + timedelta(
        days=1
    )
    last_day = last_day.isoformat() + "Z"

    results = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=first_day,
            timeMax=last_day,
            maxResults=250,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = results.get("items", [])

    for event in events:
        try:
            start = event["start"].get("dateTime").split("T")
            start = datetime.strptime(start[0], "%Y-%m-%d")
        except:
            start = event["start"].get("date")
            start = datetime.strptime(start, "%Y-%m-%d")

        if "nelc" in event["summary"].lower():
            # print(start.strftime("%Y-%m-%d"), event["summary"])
            work_days.append(start.strftime("%Y-%m-%d"))

    if len(work_days) > 0:
        print(f"-{len(work_days)} work days were found.")
    else:
        sys.exit("-No work days found for the requested month.")

    return work_days


if __name__ == "__main__":
    main()
