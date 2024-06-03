import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from calendar import monthrange
from flask_cors import CORS  # Import CORS from flask_cors
from flask import Flask, jsonify, request, render_template

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
    events = []
    # event_id = 1

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
                        # 'id': event_id,
                        'date': formatted_date,
                        'day': weekday,
                        'event': event_text.get_text(strip=True)
                    }
                    if event not in events:  # Ensure unique events
                        events.append(event)
                        # event_id += 1

    # Convert the list of events to JSON
    json_data = json.dumps(events, indent=2)
    return json_data


@app.route('/api/getEvents', methods=['POST', 'GET'])
def getEvents():
    try:
        # curr_date = "01/05/2024"
        # req_date = "03/06/2025"
        curr_date = request.json["curr_date"]
        req_date = request.json["req_date"]
        result = requested_months(curr_date, req_date)
        output = []
        for item in result:
            url = f'https://hussainiat.com/calendar/calendar.asp?month={item["month"]}&year={item["year"]}'
            output.append(scrape_calendar(url))
        return jsonify(output)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def requested_months(curr_date, req_date):
    # Parse the current and required dates
    curr_date_obj = datetime.strptime(curr_date, '%d/%m/%Y')
    req_date_obj = datetime.strptime(req_date, '%d/%m/%Y')

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


@app.route("/")
def home():
    return render_template("HomePage.html")


if __name__ == '__main__':
    app.run(debug=True, port=5001)
