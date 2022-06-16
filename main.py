from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from passlib.context import CryptContext
from Crypto.Cipher import AES
import sheetsapi #sheetsapi.py
import createQR #createQR.py
import addTeacher #addTeacher.py
import pymongo
import random
import time
import os
import codecs
# Setup

os.system('export TZ=EST+5EDT,M3.2.0/2,M11.1.0/2')
ctx = CryptContext(schemes=["sha256_crypt"])
app = Flask(__name__)
app.secret_key = 'REDACTED'
key = 'REDACTED'
iv = 'REDACTED'


client = pymongo.MongoClient("mongodb+srv://REDACTED")

db = client.get_database('DigitalHallPass')
teacherLogin = db.teacherLogin
studentInfo = db.studentInfo
passData = db.passData
config = db.config

masterSheet = 'REDACTED'


#--------------------------------------------#
def getPassData(id):
  data = {}
  _id = id
  dbData = passData.find_one({'_id':_id})
  if dbData is None: #if pass dne
    return {'fName':'ERROR. INVALID PASS'}
  dbStudent = studentInfo.find_one({'id':dbData['id']})
  if dbStudent is None:  #if student dne
    return {'fName':'ERROR. CORRUPTED PASS'}
  passActive = time.localtime(dbData['time'])
  
  passExpire = time.localtime(dbData['expire'])
  #get pass info
  data['photo'] = dbStudent['photo']
  data['fName'] = dbStudent['firstName']
  data['id'] = dbData['id']
  data['active'] = f"{passActive[3]:02d}:{passActive[4]:02d}"
  data['expires'] = f"{passExpire[3]:02d}:{passExpire[4]:02d}"
  data['teacher'] = dbData['teacher']
  data['from'] = dbData['from']
  data['to'] = dbData['to']
  data['passID'] = dbData['_id']
  return data

#--------------------------------------------#
@app.route('/countdown_timer',methods=['get'])
def countdown_timer():

  _id = request.args.get('id')
  #find the pass with id
  digitalPass = passData.find_one({'_id':_id})
  if digitalPass is None: #if pass dne
    return jsonify({'countdown':'-1:-1','isActive':'ERROR','color':'#FFCCCB'})
  expire = digitalPass['expire']
  now = int(time.time())
  remaining = expire - now
  if remaining < 0: #if pass expired
    return jsonify({'countdown':'00:00','isActive':'INVALID','color':'#FFCCCB'})
  return jsonify({'countdown':timeFormat(remaining),'isActive':'VALID','color':'#FAF0E6'})


#--------------------------------------------#
@app.route('/')
def index():
  if 'email' in session:
    return redirect(url_for('home'))
  return redirect(url_for('login'))

#--------------------------------------------#
@app.route('/login',methods=['post','get'])
def login():
  message = '' #error message
  if "username" in session:  #if already logged in, go home
    return redirect(url_for("home"))
  if request.method == 'POST':
    #get data from forms
    user = request.form.get("username").lower()
    password = request.form.get("password")
    if user is None or password is None:
      return render_template('login.html')
    #find teacher login
    userdata = teacherLogin.find_one({'email':user})
    if not userdata:
      message = 'Invalid email or password.'
      return render_template('login.html',message=message)
    #verify password
    hashed = userdata['password']
    
    if not ctx.verify(password,hashed):
      message = 'Invalid email or password.'
      return render_template('login.html',message=message)

    #add teacher data to session
    for i in userdata:
      if not i == ('_id'):
        session[i] = userdata[i]
    return redirect(url_for("home"))
    
  else:
    return render_template('login.html')

#--------------------------------------------#
@app.route('/home')
def home():
  if 'email' in session: #if logged in
    return render_template('home.html', user=session['email'], fName=session['firstName'], isAdmin=session['adminPerms'])
  return redirect(url_for('login'))
  
#--------------------------------------------#
@app.route('/logout')
def logout():
  if 'email' in session:
    for i in dict(session):
      session.pop(i, None)
    return render_template('logout.html')
  return redirect(url_for('login'))

#--------------------------------------------#
@app.route('/id',methods=['post','get'])
def id():
  message=''
  if 'email' in session: #if logged in
    return teacherError()
  elif 'origin' not in session: #if qr code has been scanned
    if request.method == 'GET':
      checksum = request.args.get('checksum') #verify code
      if checksum is None or not verifyChecksum(checksum):
        return render_template('invalid.html')
      origin = fromHex(request.args.get('origin')).decode()
      teacher = fromHex(request.args.get('teacher')).decode()
      
      session['origin'] = origin
      session['teacher'] = teacher
      return redirect(url_for('id')) #go to input id
    return redirect(url_for('login'))
  if request.method == 'POST': #if id inputted
    id = request.form.get('id')
    student = studentInfo.find_one({'id':id})
    if not student: #if student dne
      message = 'Invalid MCPS Student ID. If the ID entered is correct, please contact an administrator.'
      return render_template('id.html', message=message)
    for i in dict(student): #copy student data
      if '_id' not in i:
        session[i] = student[i]
    return redirect(url_for('passInfo'))
  return render_template('id.html', message=message)
  
#--------------------------------------------#
@app.route('/passinfo',methods=['post','get'])
def passInfo():
  if request.method == 'POST': #if pass info submitted
    isOther = False 
    destination = request.form.getlist('rad')[0]
    if destination == "": #check if "other" selected
      destination = request.form.get('otherBox')
      isOther = True

    lenData = config.find_one({'_id':'time'}) #get len of pass
    print(lenData)
    passID = config.find_one({'_id':'passID'}) #get current pass id
    passID['id'] = str(int(passID['id']) + random.randrange(1,100))
    print(passID)
    lengthOfPass = lenData['Other']
    if not isOther:
      lengthOfPass = lenData[destination]
    #copy data
    data = {}
    data['to'] = destination
    data['from'] = session['origin']
    data['id'] = session['id']
    data['teacher'] = session['teacher']
    now = int(time.time())
    end = now+lengthOfPass
    data['time'] = now
    data['expire'] = end
    data['_id'] = passID['id']
    passData.insert_one(data)
    config.delete_one({'_id':'passID'})
    config.insert_one(passID)
    return redirect(url_for('yourPass',id=data['_id']))
  return render_template('passinfo.html')
  
#--------------------------------------------#
@app.route('/yourPass',methods=['post','get'])
def yourPass():
  time.sleep(1) #ensure db updates in time
  for i in dict(session):
    session.pop(i,None)
  session['passID'] = '-1' #reset pass id
  if request.method == 'GET':
    session['passID'] = request.args.get('id') #get pass id
    data = getPassData(session['passID'])
    return render_template('pass.html',data=data)
  return render_template('pass.html')

#--------------------------------------------#
@app.route('/back',methods=['post','get'])
def back():
  message=''
  if 'email' in session: #if teacher
    return teacherError()
  if request.method == 'POST': #if id entered
    id = request.form.get('id')
    student = studentInfo.find_one({'id':id})
    data = passData.find_one({'id':id})
    if not student or not data:
      message = 'Invalid MCPS Student ID. If the ID entered is correct, your pass has already been closed.'
      return render_template('id.html', message=message)
    session['passID'] = data['_id']
    return redirect(url_for('done'))
  elif 'origin' not in session:
    if request.method == 'GET': #verify qr code
      checksum = request.args.get('checksum')
      if checksum is None or not verifyChecksum(checksum):
        return render_template('invalid.html')
      origin = fromHex(request.args.get('origin')).decode()
      teacher = fromHex(request.args.get('teacher')).decode()
      session['origin'] = origin
      session['teacher'] = teacher

      if 'passID' in session: #if pass id stored, sign out, else enter id
        return redirect(url_for('done'))
  
  return render_template('id.html', message=message)

#--------------------------------------------#
@app.route('/done')        
def done():
  data = getPassData(session['passID'])
  dbData = passData.find_one({'_id':session['passID']})
  if data is {'fName':'ERROR. INVALID PASS'}: #if pass dne
    return 'Error: Pass is already closed'
  passTeacher = data['teacher']
  passRoom = data['from']
  if passTeacher != session['teacher'] or passRoom != session['origin']:
    if not "Email" in passRoom: #email pass
      return render_template('invalid.html')
  now = int(time.time())
  if now > dbData['expire']: #dont go negative
    data['over'] = (now - dbData['expire'])/60
  else:
    data['over'] = 0
  data['active'] = str(time.strftime('%a, %d %b %Y %H:%M:%S',time.localtime(dbData['time'])))
  data['expires'] = str(time.strftime('%a, %d %b %Y %H:%M:%S',time.localtime(dbData['expire'])))
  sheetData = [data['passID'],data['id'],data['fName'],
              data['from'],data['to'],data['teacher'],
              data['active'],data['expires'],data['over']]
  teacherName = data['teacher'].split(" ")
  teacherFirst = teacherName[0]
  teacherLast = teacherName[1]
  teacherData = teacherLogin.find_one({'firstName':teacherFirst,'lastName':teacherLast})
  sheetID = teacherData['sheet']
  print(sheetData)
  sheetsapi.insert(sheetID,sheetData) #send to google sheets
  sheetsapi.insert(masterSheet,sheetData)
  passData.delete_one(dbData)

  for i in dict(session): #clear session
    session.pop(i,None)
  return render_template('closed.html')

#--------------------------------------------#
@app.route('/qr',methods=['post','get'])
def qr():
  if not 'email' in session: #if not logged in
    return redirect(url_for('login'))
  if request.method == 'POST':
    room = request.form.get("room")
    try:
      name = session['firstName']+" "+session['lastName']
    except:
      for i in dict(session):
        session.pop(i,None)
      return 'A fatal error has occured. You have been logged out'
    qrcode = createQR.gen(room,name)[6:]
    return redirect(url_for('static',filename=qrcode))
  return render_template('qr.html')

#--------------------------------------------#
@app.route('/addteacher',methods=['post','get'])
def addteacher():
  if not 'email' in session: #if not logged in
    return redirect(url_for('login'))
  if request.method == 'POST': #if info inputted
    email = request.form.get('email')
    first = request.form.get('fname')
    last = request.form.get('lname')
    password = request.form.get('password')
    admin = request.form.get('admin')
    if not admin == "1" or not admin == "0":
      admin = "0"
    addTeacher.create(email,password,first,last,admin) #create teacher
    return render_template('success.html')
  return render_template('addTeacher.html')

#--------------------------------------------#
@app.route('/sendapass',methods=['post','get'])
def sendapass():
  if not 'email' in session: #if not logged in
    return redirect(url_for('login'))
  for i in dict(session):
    if "student" in i:
      session.pop(i,None)
    
  if request.method == 'POST': #if pass inputted
    student = request.form.get('student')
    destination = request.form.get('destination')
    reason = request.form.get('reason')
    today = time.localtime()
    date = time.strftime("%a %b %d %Y ",today)
    start_tmp = date+request.form.get('start')+":00"
    end_tmp = date+request.form.get('end')+":00"
    start = int(time.mktime(time.strptime(start_tmp,"%a %b %d %Y %H:%M:%S")))
    end = int(time.mktime(time.strptime(end_tmp,"%a %b %d %Y %H:%M:%S")))
    data = {}
    passID = config.find_one({'_id':'passID'})
    passID['id'] = str(int(passID['id']) + random.randrange(1,100))

    data['to'] = destination
    data['from'] = "Email Hall Pass"
    data['id'] = student
    data['teacher'] = session['firstName']+" "+session['lastName']
    data['time'] = start
    data['expire'] = end
    data['_id'] = passID['id']
    passData.insert_one(data)
    config.delete_one({'_id':'passID'})
    config.insert_one(passID)
    url = url_for('yourPass',id=data['_id'])
    session['studentEmail'] = f"{student}@mcpsmd.net"
    session['studentPass'] = createQR.root+url
    session['studentReason'] = reason

    return redirect(url_for('email'))
  return render_template('sendapass.html')

#--------------------------------------------#
@app.route('/email')
def email():
  if not 'email' in session:
    return redirect(url_for('login'))
  return render_template('email.html')

#--------------------------------------------#
def teacherError():
  return render_template('teacherError.html')

#--------------------------------------------#
def timeFormat(timeLeft):
  minutes = timeLeft // 60
  seconds = timeLeft % 60
  return f"{minutes:02d}:{seconds:02d}"

#--------------------------------------------#
def fromHex(input):
  return codecs.decode(input,"hex")

#--------------------------------------------#
def verifyChecksum(checksum):
  enc = AES.new(fromHex(key),AES.MODE_CFB,fromHex(iv))
  out = enc.decrypt(fromHex(checksum))
  try:
    return (key in out.decode())
  except:
    return False

if __name__ == "__main__":
	port = int(os.environ.get('PORT', 5000))
	app.run('0.0.0.0', port=port)
