import cv2
import pytesseract
import numpy as np
from PIL import ImageGrab
from pyzbar.pyzbar import decode
from datetime import datetime
import mysql.connector

# INIT DB MYSQL CONNECTOR
db = mysql.connector.connect(
    host="localhost", user="root", password="password", database="parkir_management"
)

mycursor = db.cursor()
print("db:", db)
# QUERY INSERT DATA TO DB
insert = "INSERT INTO parkir_management.motor (no_plat, stnk, date, time ) VALUES (%s, %s, %s, %s)"
checker = "SELECT * FROM parkir_management.motor WHERE stnk='"
# INIT VIDEO CAPTURE (PLAT NOMOR & BARCODE)
videoPlat = cv2.VideoCapture(-1)  # SESUAIKAN DENGAN DEVICES
videoBarcode = cv2.VideoCapture(1)  # SESUAIKAN DENGAN DEVICES (ganti cv2.videocapture untuk record dari kamera eksternal ke2)
videoPlat.set(3, 480)
videoPlat.set(4, 280)
videoBarcode.set(3, 480)
videoBarcode.set(4, 280)


def captureScreen(bbox=(300, 300, 1500, 1000)):
    capScr = np.array(ImageGrab.grab(bbox))
    capScr = cv2.cvtColor(capScr, cv2.COLOR_RGB2BGR)
    return capScr


# LOOPING VIDEO
while True:
    timer = cv2.getTickCount()
    ret1, imgPlat = videoPlat.read()
    ret2, imgBarcode = videoBarcode.read()
    # DETECTING CHARACTERES
    if ret1:
        cv2.imshow("VIDEO PLAT NOMOR", imgPlat)

    # DETECTING BARCODES
    if ret2:
        #LOOPING FOR PROCESSING, VALIDATION, AND INSERT DATA
        for barcode in decode(imgBarcode):
            myData = barcode.data.decode("utf-8")
            print(myData)
            pts = np.array([barcode.polygon], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(imgBarcode, [pts], True, (255, 0, 255), 5)
            pts2 = barcode.rect
            cv2.putText(
                imgBarcode,
                myData,
                (pts2[0], pts2[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (225, 0, 225),
                2,
            )
        
            # IF DATA BARCODE IS TRUE, THEN CAPTURE PLAT NOMOR
            # OCR PROCESSING
            if myData != '':
                cv2.imwrite("plat.png", imgPlat)
                # conver gambar plat to grayscale
                image = cv2.imread("plat.png")
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                # preprocessing
                gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                gray = cv2.medianBlur(gray, 3)

                # apply OCR to it
                kernel = np.ones((5, 5), np.uint8)
                gray = cv2.dilate(gray, kernel, iterations=1)

                # olah gambar after processing dengan tessereact
                hasil_ocr = pytesseract.image_to_string(gray)
                print(hasil_ocr)

                # VALIDATION
                if hasil_ocr == "" or myData == "":
                    print("Sistem tidak membaca data plat atau qrcode!")
                if hasil_ocr != "" and myData != "":
                    # eksekusi checker data basedon stnk
                    mycursor.execute(checker + myData + "'" + "AND no_plat='" + hasil_ocr + "'")
                    checkerValue = mycursor.fetchall()
                    
                    # check existing data from database
                    if checkerValue:
                        print("Data telah terdafatar pada database sebelumnya, Open Gate!")
                    if len(checkerValue) == 0:
                        dateCaptured = datetime.today().strftime("%Y-%m-%d")
                        timeCaptured = datetime.today().strftime("%H:%M:%S")
                        val = (hasil_ocr, myData, dateCaptured, timeCaptured)
                        mycursor.execute(insert, val)
                        print("Data telah terecord, Open Gate!")
                db.commit()
        cv2.imshow("VIDEO BARCODE:", imgBarcode)

    #exit program? press "q"
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

videoPlat.release()
videoBarcode.release()
cv2.destroyAllWindows()
