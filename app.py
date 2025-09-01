import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from calendar import monthrange
from flask_cors import CORS  # Import CORS from flask_cors
from flask import Flask, jsonify, request, render_template
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from math import ceil

app = Flask(__name__, template_folder='template')
CORS(app, resources={r"/api/*": {"origins": "*"}})


def scrape_calendar(url):
    # Parse the URL to get year and month from the query string
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    # Default to 2024 if not specified
    year = int(query_params.get('year', [2024])[0])
    # Default to July if not specified
    month = int(query_params.get('month', [7])[0])

    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)"
    }
    payload = ""

    # Function to make the request with retries
    def make_request_with_retries(url, headers, payload, max_retries=5):
        retries = 0
        while retries < max_retries:
            try:
                response = requests.request(
                    "GET", url, data=payload, headers=headers, verify=False)
                response.raise_for_status()  # Raise HTTPError for bad responses
                return response
            except requests.exceptions.HTTPError as e:
                if response.status_code == 504:  # Handle 504 specifically
                    retries += 1
                    wait_time = 2 ** retries  # Exponential backoff
                    print(
                        f"504 error encountered. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise e
        raise Exception(
            f"Failed to retrieve data after {max_retries} attempts")

    # Send a GET request to the URL with retries
    response = make_request_with_retries(url, headersList, payload)

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the table that contains the calendar data
    table = soup.find('table', bordercolor='#C0C0C0')
    rows = table.find_all('tr')[1:]  # Skip the header row

    # Initialize a list to hold the data
    events = []

    # Get the maximum valid day for the given month and year
    max_day = monthrange(year, month)[1]

    # Iterate through each row in the table
    for row in rows:
        cols = row.find_all('td')
        for col in cols:
            # Handle multiple colors for the date
            day = ''.join(filter(str.isdigit, col.text.split('/')[0].strip()))

            if day.isdigit() and 1 <= int(day) <= max_day:
                # Calculate date and day of the week
                eng_date = datetime(year, month, int(day))
                weekday = eng_date.strftime('%A')
                formatted_date = eng_date.strftime('%d/%m/%Y')

                # Get event details if any
                event_texts = col.find_all('b')
                for event_text in event_texts:
                    event = {
                        'date': formatted_date,
                        'day': weekday,
                        'event': event_text.get_text(strip=True)
                    }
                    if event not in events:  # Ensure unique events
                        events.append(event)

    # Convert the list of events to JSON
    json_data = json.dumps(events, indent=2)
    return json_data


def scrape_month_calendar(url):
    # Parse the URL to get year and month from the query string
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    # Default to 2024 if not specified
    year = int(query_params.get('year', [2024])[0])
    # Default to July if not specified
    month = int(query_params.get('month', [7])[0])

    # Send a GET request to the URL
    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)"
    }
    payload = ""
    response = requests.request("GET", url, data=payload,  headers=headersList)
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    # print(soup)
    # Find the table that contains the calendar data
    table = soup.find('table', bordercolor='#C0C0C0')
    rows = table.find_all('tr')[1:]  # Skip the header row

    # Initialize a list to hold the data
    # events = []
    out_event = {}
    # Get the maximum valid day for the given month and year
    max_day = monthrange(year, month)[1]

    # Iterate through each row in the table
    for row in rows:
        cols = row.find_all('td')
        for col in cols:
            # Handle multiple colors for the date
            day = ''.join(filter(str.isdigit, col.text.split('/')[0].strip()))

            if day.isdigit() and 1 <= int(day) <= max_day:
                # Calculate date and day of the week
                eng_date = datetime(year, month, int(day))
                weekday = eng_date.strftime('%A')
                # formatted_date = eng_date.strftime('%d/%m/%Y')
                formatted_date = int(day)

                # Get event details if any
                event_texts = col.find_all('b')
                for event_text in event_texts:
                    event = {
                        'date': formatted_date,
                        'day': weekday,
                        'event': event_text.get_text(strip=True)
                    }
                    if event['date'] not in out_event:  # Ensure unique events
                        out_event[event['date']] = event['event']
                        # events.append(event)
    # Convert the list of events to JSON
    json_data = json.dumps(out_event, indent=2)
    return json_data


@app.route('/api/addCalendar', methods=['POST'])
def getEvents():
    try:
        # curr_date = "01/05/2024"
        # req_date = "03/06/2025"
        curr_date = request.json["curr_date"]
        req_date = request.json["req_date"]
        refresh_token = request.json["refresh_token"]
        provider_token = request.headers.get('Authorization').split(' ')[1]
        print(curr_date, req_date)
        result = requested_months(curr_date, req_date)
        print(result)
        credentials = Credentials(
            token=provider_token, refresh_token=refresh_token, scopes=['https://www.googleapis.com/auth/calendar'])
        print(credentials)
        # if not credentials or not credentials.valid:
        #     if credentials and credentials.expired and credentials.refresh_token:
        #         credentials.refresh(Request())
        # else:
        #     return jsonify({"error": "Invalid credentials"}), 401
        for item in result:
            url = f'https://hussainiat.com/calendar/calendar.asp?month={item["month"]}&year={item["year"]}'
            out = scrape_calendar(url)
            month_event_data = json.loads(out)
            print("month_event_data", month_event_data)
            add_event(month_event_data, credentials)
        print("status")
        return jsonify({"status": "success", "message": "Events added successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def add_event(month_event_data, credentials):
    service = build('calendar', 'v3', credentials=credentials)
    print("events", month_event_data)
    for events in month_event_data:
        event_date = events['date']  # Expected format: 'YYYY-MM-DD'
        date_obj = datetime.strptime(event_date, '%d/%m/%Y')
        # Convert to desired format 'YYYY-MM-DD'
        formatted_event_date = date_obj.strftime('%Y-%m-%d')
        event_time = '09:30'  # Expected format: 'HH:MM'

        start_datetime_str = f"{formatted_event_date}T{event_time}:00"
        start_datetime = datetime.strptime(
            start_datetime_str, '%Y-%m-%dT%H:%M:%S')
        formatted_datetime_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        time_to_bell = int(
            (start_datetime - start_datetime.replace(hour=9, minute=0)).total_seconds() // 60)

        # time_to_bell.strftime("%Y-%m-%dT%H:%M:%S")
        print(time_to_bell)
        # end_datetime = start_datetime + timedelta(hours=1)
        event_body = {
            'summary': events['event'],
            'start': {
                'date': formatted_event_date,
                'timeZone': 'UTC',
            },
            'end': {
                'date': formatted_event_date,
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    # Email notification at 9:00 AM
                    {'method': 'email', 'minutes': time_to_bell}
                ],
            },
        }
        try:
            # Add the event to the calendar
            created_event = service.events().insert(
                calendarId='primary', body=event_body).execute()
            print('Event created: %s' % (created_event.get('htmlLink')))

        except Exception as e:
            print(f'An error occurred: {e}')
            continue  # Continue to the next event


@ app.route('/api/getCalendar', methods=['POST'])
def getCalendar():
    try:
        req_date = request.json["req_month"]
        req_year = request.json["req_year"]

        url = f'https://hussainiat.com/calendar/calendar.asp?month={req_date}&year={req_year}'
        output = scrape_month_calendar(url)
        return jsonify(output)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def requested_months(curr_date, req_date):
    # Parse the current and required dates
    curr_date_obj = datetime.strptime(curr_date, '%Y/%m/%d')
    req_date_obj = datetime.strptime(req_date, '%Y/%m/%d')

    # Initialize the results list and current tracking variables
    combine_date = []
    curr_month = curr_date_obj.month
    curr_year = curr_date_obj.year

    # Extract month and year from required date
    req_month = req_date_obj.month
    req_year = req_date_obj.year

    # Iterate from the current year to the required year
    while curr_year < req_year or (curr_year == req_year and curr_month <= req_month):
        combine_date.append({"month": curr_month, "year": curr_year})

        # Increment month and adjust year if needed
        if curr_month == 12:
            curr_month = 1
            curr_year += 1
        else:
            curr_month += 1

    # Handle the scenario where current year equals required year and the months range within the same year
    if curr_year == req_year:
        for i in range(curr_month, req_month + 1):
            combine_date.append({"month": i, "year": req_year})

    return combine_date


@ app.route("/")
def home():
    return render_template("HomePage.html")


if __name__ == '__main__':
    app.run(debug=True, port=5001)
