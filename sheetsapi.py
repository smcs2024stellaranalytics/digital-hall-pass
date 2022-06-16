import pygsheets

auth = pygsheets.authorize(service_account_file='credentials.json')

def insert(id,data):
  sheet = auth.open_by_key(id)[0]
  sheet.append_table(data)