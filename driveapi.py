from __future__ import print_function
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


SCOPES = ['https://www.googleapis.com/auth/drive']
KEY_FILE_LOCATION = 'credentials.json'

creds = ServiceAccountCredentials.from_json_keyfile_name(
    KEY_FILE_LOCATION, SCOPES)
service = build('drive', 'v3', credentials=creds)



def insert(name, path):
  media = MediaFileUpload(path,
                          mimetype='text/csv')
  id = service.files().create(body={'name': name,'mimeType': 'application/vnd.google-apps.spreadsheet'},
                                      media_body=media,
                                      fields='id').execute()['id']
  return id

def share(email, id):
  service.permissions().create(body={"role":"writer", "type":"user",'emailAddress':email}, fileId=id).execute()


def reset():
  results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
  items = results.get('files', [])
  for item in items:
    service.files().delete(fileId=item['id']).execute()
    
def view():
  try:
      results = service.files().list(
          pageSize=10, fields="nextPageToken, files(id, name)").execute()
      items = results.get('files', [])
  
      if not items:
          print('No files found.')
          exit(0)
      print('Files:')
      for item in items:
          print(u'{0} ({1})'.format(item['name'], item['id']))
  except HttpError as error:
      # TODO(developer) - Handle errors from drive API.
      print(f'An error occurred: {error}')

if __name__ == '__main__':
  view()

