import os
from gcloud_parser.gcloud_parser import GcloudParser
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import datetime
import time

PATH = '/home/lutz/grive/Belege'

# SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# SCOPE = ['https://spreadsheets.google.com/feeds']

# SCOPES = ['https://www.googleapis.com/auth/drive']
#
# # The ID and range of a sample spreadsheet.
# SAMPLE_SPREADSHEET_ID = 'Einkaeufe'
# SAMPLE_RANGE_NAME = 'Liste!A1:D100'

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1lKnQ1nqVViIDG4Kww_XiDm8U51AWzhb1dA63gyuuAJY'
SAMPLE_RANGE_NAME = 'Liste!A:L'

known_categories = dict()

if __name__ == '__main__':
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../receipt-parser-f50b734aa273.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])
    scanned_filenames = []
    next_row = 1
    if not values:
        print('No data found.')
    else:
        print('Name, Major:')
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            print(str(next_row) + ' - ' + str(row))
            if not row[1] in known_categories.keys():
                if row[9]:
                    known_categories[row[1]] = row[9]
            next_row += 1
            if len(row) >= 12:
                if not row[11] in scanned_filenames:
                    scanned_filenames.append(row[11])
    print('Next Row ' + str(next_row))
    # code.interact(banner='', local=locals())

    parser = GcloudParser()
    files = os.listdir(PATH)
    purchases = []
    for file in files:
        full_name = os.path.join(PATH, file)
        if full_name in scanned_filenames:
            continue
        if os.path.isfile(full_name) and full_name[-4:] == '.pdf':
            articles, dates, markets = parser.parse_pdf(full_name)
            if len(markets) > 0:
                market = markets[0]
            else:
                market = 'unknown'
            if len(dates) > 0:
                date = dates[0]
            else:
                date = 'unknown'
            for article in articles:
                purchases.append({
                    'date': date,
                    'market': market,
                    'article': article['name'],
                    'price': article['price'],
                    'filename': full_name
                })
    for purch in purchases:
        target_range = 'Liste!A{num}:L{num}'.format(num=next_row)
        iso_week = ''
        iso_month = ''
        try:
            iso_week = datetime.datetime.strptime(purch['date'], '%Y-%m-%d').isocalendar()[1]
            iso_month = datetime.datetime.strptime(purch['date'], '%Y-%m-%d').month
        except:
            pass
        category = ''
        if purch['article'] in known_categories.keys():
            category = known_categories[purch['article']]
        values = [purch['date'],
                  purch['article'],
                  'Nein',
                  purch['market'],
                  '',
                  1,
                  purch['price'],
                  purch['price'],
                  iso_week,
                  category,
                  iso_month,
                  purch['filename']
                  ]
        print(purch['date'] + ' ' + purch['market'] + ' ' + purch['article'] + ' ' + str(purch['price']) + ' ' + purch['filename'])
        sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=target_range, body={'values': [values]},
                              valueInputOption='USER_ENTERED').execute()
        next_row += 1
        time.sleep(1.5) # wait a moment such that we do not exceed google write quotas
