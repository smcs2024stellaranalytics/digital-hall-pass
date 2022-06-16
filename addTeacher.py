import pymongo
from passlib.context import CryptContext
import driveapi

ctx = CryptContext(schemes=["sha256_crypt"])
client = pymongo.MongoClient("mongodb+srv://smcs2024stellaranalytics:9U36Z09ANCgvAejV@digitalhallpass.j2d99.mongodb.net/DigitalHallPass?retryWrites=true&w=majority")
db = client.get_database('DigitalHallPass')
teacherLogin = db.teacherLogin

def create(email,password,fname,lname,isAdmin):
  isAdmin = int(isAdmin)
  hashed = ctx.hash(password)
  id = driveapi.insert(f'digital-hallpass-{fname}-{lname}','static/template.csv')
  driveapi.share(email, id)

  input = {'email':email, 'password':hashed, 'firstName':fname, 'lastName':lname, 'adminPerms':isAdmin, 'sheet':id}
  teacherLogin.insert_one(input)
  