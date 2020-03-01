import os
from gcloud_parser.gcloud_parser import GcloudParser
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import datetime
import time
import configparser
import argparse


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings', dest='settings', help='Provide path to settings file', required=True)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_arguments()
    conf = configparser.ConfigParser()
    conf.read(args.settings)
    spreadsheet_id = conf.get('sheets', 'spreadsheet_id')
    spreadsheet_range = conf.get('sheets', 'spreadsheet_range')
    oauth_token_path = conf.get('sheets', 'oauth_token')
    oauth_pickle_path = conf.get('sheets', 'oauth_pickle')
    receipts_base_path = conf.get('drive', 'receipts_path')
    known_categories = dict()
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(oauth_pickle_path):
        with open(oauth_pickle_path, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                oauth_token_path, SCOPES)
                # '../receipt-parser-f50b734aa273.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(oauth_pickle_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=spreadsheet_range).execute()
    values = result.get('values', [])
    scanned_filenames = []
    next_row = 1
    if not values:
        print('No data found.')
    else:
        for row in values:
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
    files = os.listdir(receipts_base_path)
    purchases = []
    for file in files:
        full_name = os.path.join(receipts_base_path, file)
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
    range_base = spreadsheet_range.split('!')[0]
    for purch in purchases:
        target_range = '{range_base}!A{num}:L{num}'.format(range_base=range_base, num=next_row)
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
        print(purch['date'] + ' ' + purch['market'] + ' ' + purch['article'] + ' ' + str(purch['price']) +
              ' ' + purch['filename'])
        sheet.values().update(spreadsheetId=spreadsheet_id, range=target_range, body={'values': [values]},
                              valueInputOption='USER_ENTERED').execute()
        next_row += 1
        time.sleep(1.5) # wait a moment such that we do not exceed google write quotas
