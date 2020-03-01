import pytesseract as pts
from pdf2image import convert_from_path

PATH = '../../grive/Belege/Gescannt_20200213-1926.pdf'
pages = convert_from_path(PATH, 500)
for page in pages:
    test_str = pts.image_to_data(page, lang='deu', config='--psm 6')
    print(test_str)