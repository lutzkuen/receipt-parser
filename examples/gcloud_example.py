from google.cloud import vision
import io
from pdf2image import convert_from_path
import os


PATH = '../../grive/Belege/Gescannt_20200208-1357.pdf'
pages = convert_from_path(PATH, 501)
client = vision.ImageAnnotatorClient()
for page in pages:
    page.save('tmp.jpg')
    with io.open('tmp.jpg', 'rb') as image_file:
        content = image_file.read()
    os.system('rm tmp.jpg')
    image = vision.types.Image(content=content)
    response = client.text_detection(image=image)
    print(response.text_annotations[0].description)
