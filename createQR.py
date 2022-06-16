import codecs
import qrcode
from Crypto.Cipher import AES
from PIL import ImageFont
from PIL import ImageDraw 
from PIL import Image
import os

key = '3777ef1f99eb0afbfdcf1a2618d5f2ab7c709983c4059631634e330bf24e4b6a'
iv = '4345dd9e4389a77347b495294cc2cac7'
root = 'https://digital-hall-pass.herokuapp.com/'

def fromHex(input):
  return codecs.decode(input,"hex")


def makeChecksum(room,teacher):
  newRoom = fromHex(room)
  newTeacher = fromHex(teacher)
  checkString = newRoom+newTeacher+key.encode()
  enc = AES.new(fromHex(key), AES.MODE_CFB, fromHex(iv))
  ct = enc.encrypt(checkString).hex()
  return ct
  
def makeLeaveCode(room, teacher):

  ct = makeChecksum(room, teacher)
  first = f"{root}/id?origin={room}&teacher={teacher}&checksum={ct}"

  qr = qrcode.QRCode(
      version=1,
      error_correction=qrcode.constants.ERROR_CORRECT_L,
      box_size=10,
      border=20,
  )
  qr.add_data(first)
  qr.make(fit=True)
  img = qr.make_image(fill_color="black", back_color="white")
  
  draw = ImageDraw.Draw(img)
  # font = ImageFont.truetype(<font-file>, <font-size>)
  font = ImageFont.truetype("Arial.ttf", 64)
  # draw.text((x, y),"Sample Text",(r,g,b))
  width, height = img.size
  print(width,height)
  draw.text((width/2, int(height*0.94)),f"{fromHex(room).decode()} Sign Out",0,font=font, anchor="md")
  draw.text((width/2, int(height*0.06)),f"Digital Hall Pass",0,font=font, anchor="ma")
  return img

def makeReturnCode(room, teacher):
  ct = makeChecksum(room, teacher)
  end = f"{root}/back?origin={room}&teacher={teacher}&checksum={ct}"

  qr = qrcode.QRCode(
      version=1,
      error_correction=qrcode.constants.ERROR_CORRECT_L,
      box_size=10,
      border=20,
  )
  qr.add_data(end)
  qr.make(fit=True)
  img = qr.make_image(fill_color="black", back_color="white")
  
  draw = ImageDraw.Draw(img)
  # font = ImageFont.truetype(<font-file>, <font-size>)
  font = ImageFont.truetype("Arial.ttf", 64)
  # draw.text((x, y),"Sample Text",(r,g,b))
  width, height = img.size
  draw.text((width/2, int(height*0.94)),f"{fromHex(room).decode()} Sign In",0,font=font, anchor="md")
  draw.text((width/2, int(height*0.06)),f"Digital Hall Pass",0,font=font, anchor="ma")
  
  return width,height,img


def gen(room, teacher):
  room = room.encode().hex()
  teacher = teacher.encode().hex()
  img1 = makeLeaveCode(room,teacher)
  w,h,img2 = makeReturnCode(room,teacher)	
  dst = Image.new('RGB', (w+w, h))
  dst.paste(img1, (0, 0))
  dst.paste(img2, (w, 0))
  teacher = fromHex(teacher).decode()
  room = fromHex(room).decode()
  dst.save(os.path.join('static','tmp', f"{teacher}_{room}.png"))
  return os.path.join('static','tmp', f"{teacher}_{room}.png")

if __name__ == "__main__":
  gen("Room 999","Admin Admin")
