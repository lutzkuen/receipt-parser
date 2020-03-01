from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os
from google.auth.transport.requests import Request


spreadsheet_id = '1kB3Frs2oRIh6d4hD3FL1RDNYhry3dRSc9a7sSxNTXDI'
spreadsheet_range = 'Sheet1!A1:A1'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
oauth_token_path = '../Downloads/client_secret_339936403154-d4igrfc42tefqoi6usscasv1t9jj2fjr.apps.googleusercontent.com.json'
creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('../../token.pickle'):
    with open('../../token.pickle', 'rb') as token:
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
    with open('../../token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('sheets', 'v4', credentials=creds)

# Call the Sheets API
sheet = service.spreadsheets()
result = sheet.values().get(spreadsheetId=spreadsheet_id,
                            range=spreadsheet_range).execute()
values = result.get('values', [])
print('Before Update')
print(values)
# perform an update
sheet.values().update(spreadsheetId=spreadsheet_id, range=spreadsheet_range, body={'values': [['Hello World']]},
                              valueInputOption='USER_ENTERED').execute()
result = sheet.values().get(spreadsheetId=spreadsheet_id,
                            range=spreadsheet_range).execute()
values = result.get('values', [])
print('After Update')
print(values)
