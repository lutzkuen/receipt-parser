import numpy as np
from google.cloud import vision
import enchant
from pdf2image import convert_from_path
import datetime
import io
import os
import pickle
import code

SKIPWORDS = ['eur', 'stk', 'x']
STOPWORDS = ['summe', 'visa', 'mwst', 'brutto', 'netto', 'zahlen', 'kreditkarte', 'ust-id-nr', 'rück geld']
MARKETS = ['drogerie', 'lidl', 'rewe', 'real', 'allguth', 'dm']
BLACKLIST_WORDS = ['steuer-nr', 'eur*', 'pfand']


def is_number(in_str):
    try:
        _ = float(in_str)
        return True
    except Exception as e:
        return False


def is_decimal(i_num):
    if not is_number(i_num):
        return False
    if round(float(i_num)) != float(i_num):
        return True
    else:
        return False

def blacklist(label):
    if len(label) < 5:
        return False
    for blacklist_word in BLACKLIST_WORDS:
        if blacklist_word in label.lower():
            return False
    return True

class TextBlock:
    def __init__(self, vertex, label):
        self.vertices = vertex.bounding_poly.vertices
        self.description = vertex.description
        self.label = label


class GcloudParser:
    def __init__(self, debug=False, min_length=5, max_height=1):
        self.debug = debug
        self.min_length = min_length
        self.max_height = max_height
        self.dict_ger = enchant.Dict('de_DE')
        self.client = vision.ImageAnnotatorClient()
        self.allowed_labels = ['article', 'price', 'market', 'address', 'date', 'misc']

    def parse_date(self, date_str):
        for fmt in ['%d.%m.%y', '%Y-%m-%d', '%d.%m.%y %H:%M', '%d.%m.%Y', '%d.%m.%y %H:%M']:
            for substr in date_str.split(' '):
                try:
                    new_purch_date = datetime.datetime.strptime(substr, fmt).strftime('%Y-%m-%d')
                    return new_purch_date
                except Exception as e:
                    pass
        return None

    def check_price(self, field_val):
        if ' ' in field_val:
            pr = field_val.split(' ')[0]
        else:
            pr = field_val
        pr = pr.replace('B','').replace('A','')
        pr = pr.replace(',', '.')
        if is_decimal(pr):
            # print(str(pr) + ' is decimal')
            return pr
        else:
            return False

    def parse_pdf(self, path):
        pages = convert_from_path(path, 500)
        articles = []
        dates = []
        markets = []
        for page in pages:
            pkl_name = path.replace('.pdf', '.pkl')
            if os.path.isfile(pkl_name):
                gcloud_response = pickle.load(open(pkl_name, 'rb'))
            else:
                page.save('tmp.jpg')
                gcloud_response = self.detect_text('tmp.jpg')
                pickle.dump(gcloud_response, open(pkl_name, 'wb'))
            # os.system('rm tmp.jpg')
            _art, _dat, _mar = self.parse_response(gcloud_response)
            articles += _art
            dates += _dat
            markets += _mar
        # print(articles)
        # print(markets)
        # print(dates)
        return articles, dates, markets

    def detect_text(self, path):
        """Detects text in the file."""
        with io.open(path, 'rb') as image_file:
            content = image_file.read()
        image = vision.types.Image(content=content)
        response = self.client.text_detection(image=image)
        if response.error.message:
            raise Exception(
                '{}\nFor more info on error messages, check: '
                'https://cloud.google.com/apis/design/errors'.format(
                    response.error.message))
        return response

    def is_integer(self, text_body):
        try:
            _ = int(text_body)
        except:
            return False
        if round(float(text_body)) == float(text_body):
            return True
        return False

    def check_annotation_type(self, text_body):
        if self.check_price(text_body):
            return 'number'
        if self.parse_date(text_body):
            return 'date'
        if self.is_integer(text_body):
            return 'int'
        if self.check_market(text_body):
            return 'market'
        return 'text'

    def check_market(self, text_body):
        for market in MARKETS:
            if market in text_body.lower().split(' '):
                return market
        if text_body[0] == 'L' and text_body[2:4] == 'DL' and len(text_body) < 7:
            # we will take this for a LIDL. The I is written so weird it produces a differenct character every time
            return 'lidl'
        if text_body[0:3] == 'LID' and len(text_body) < 7:
            return 'lidl'
        if text_body[0:3] == 'LDL' and len(text_body) < 6:
            return 'lidl'
        if text_body[0:4] == 'LinL':
            return 'lidl'
        return None

    def check_article_name(self, article_name):
        num_alnum = 0
        for c in article_name:
            if c.isalpha():
                num_alnum += 1
        if num_alnum <= 2:
            return False
        return True

    def parse_response(self, gcloud_response):
        articles = []
        dates = []
        markets = []
        seen_indexes = []
        seen_prices = []
        parsed_y = 0
        base_ann = gcloud_response.text_annotations[0]
        g_xmin = np.min([v.x for v in base_ann.bounding_poly.vertices])
        g_xmax = np.max([v.x for v in base_ann.bounding_poly.vertices])
        g_ymin = np.min([v.y for v in base_ann.bounding_poly.vertices])
        g_ymax = np.max([v.y for v in base_ann.bounding_poly.vertices])
        break_this = False
        sorted_annotations = gcloud_response.text_annotations[1:]
        # sorted_annotations = sorted(gcloud_response.text_annotations[1:],
        #                             key=lambda x: x.bounding_poly.vertices[0].y)
        current_name = ''
        for i, annotation in enumerate(sorted_annotations):
            skip_this = False
            for stopword in STOPWORDS:
                if stopword in annotation.description.lower().split(' '):
                    if self.debug:
                        print('Stop Word: ' + str(annotation.description))
                    break_this = True
            for skipword in SKIPWORDS:
                if skipword in annotation.description.lower().split(' '):
                    if self.debug:
                        print('Skipping ' + str(annotation.description))
                    skip_this = True
            for skipword in BLACKLIST_WORDS:
                if skipword in annotation.description.lower().split(' '):
                    if self.debug:
                        print('Skipping ' + str(annotation.description))
                    skip_this = True
            if skip_this:
                continue
            if i in seen_indexes:
                # print('Skipping ' + annotation.description)
                continue
            t_type = self.check_annotation_type(annotation.description)
            if self.debug:
                print(annotation.description + ' ' + t_type)
            if t_type == 'text':
                if break_this:
                    continue
                used_idx = []
                used_pr = []
                xmin = np.min([v.x for v in annotation.bounding_poly.vertices])
                xmax = np.max([v.x for v in annotation.bounding_poly.vertices])
                ymin = np.min([v.y for v in annotation.bounding_poly.vertices])
                ymax = np.max([v.y for v in annotation.bounding_poly.vertices])
                if xmax > g_xmax/2:
                    continue
                if (ymax + ymin)/2 < parsed_y:
                    # print('Skipping ' + annotation.description + ' ' + str(ymax) + ' ' + str(parsed_y))
                    continue
                line_height = ymax - ymin
                # look for a price that is in the same line on the far right
                current_price = None
                current_name += annotation.description
                y_current = 0
                for j, p_ann in enumerate(sorted_annotations):
                    if i == j:
                        continue
                    skip_this = False
                    for skipword in SKIPWORDS+BLACKLIST_WORDS+STOPWORDS:
                        if skipword in p_ann.description.lower().split(' '):
                            skip_this = True
                    if skip_this:
                        continue
                    p_xmin = np.min([v.x for v in p_ann.bounding_poly.vertices])
                    p_xmax = np.max([v.x for v in p_ann.bounding_poly.vertices])
                    p_ymin = np.min([v.y for v in p_ann.bounding_poly.vertices])
                    p_ymax = np.max([v.y for v in p_ann.bounding_poly.vertices])
                    if p_ymax < ymin or p_ymin > ymax:
                        continue
                    line_overlap = np.min([p_ymax-ymin, ymax-p_ymin]) / np.max([p_ymax-p_ymin, ymax-ymin])
                    if line_overlap < 0.5:
                        continue
                    p_type = self.check_annotation_type(p_ann.description)
                    if p_type == 'number':
                        if p_xmax < g_xmax / 2:
                            continue
                        if j in seen_prices:
                            continue
                        # code.interact(banner='', local=locals())
                        if p_ymax < ymin or p_ymin > ymax or p_xmax < xmax or p_ymin < y_current:
                            if current_price or p_ymin > ymin + 2*line_height:
                                continue
                        if self.debug:
                            print('Checking ' + p_ann.description)
                        y_current = p_ymin
                        used_pr.append(j)
                        current_price = self.check_price(p_ann.description)
                        if self.debug:
                            print('New price ' + str(current_price))
                        parsed_y = max(parsed_y, (p_ymax + p_ymin) / 2)
                    elif p_type == 'text':
                        if p_xmax > g_xmax / 2:
                            continue
                        if p_ymax < ymin or p_ymin > ymax or ( y_current > 0 and p_ymin > y_current):
                            continue
                        used_idx.append(j)
                        parsed_y = max(parsed_y, (p_ymax + p_ymin) / 2)
                        if self.debug:
                            print('Appending ' + current_name + ' ' + p_ann.description)
                        current_name += ' ' + p_ann.description
                if self.debug:
                    print(current_name + ' ' + str(current_price))
                if current_price:
                    seen_prices += used_pr
                    seen_indexes += used_idx
                    skip_this = False
                    # for checkword in BLACKLIST_WORDS + SKIPWORDS + STOPWORDS:
                    #     if checkword in current_name.lower():
                    #         skip_this = True
                    if self.debug:
                        print(current_name.lower())
                    if not self.check_article_name(current_name):
                        skip_this = True
                    if not skip_this:
                        if self.debug:
                            print('Adding ' + current_name + ' ' + str(current_price))
                        articles.append({
                            'name': current_name,
                            'price': current_price
                        })
            elif t_type == 'date':
                dates.append(self.parse_date(annotation.description))
            elif t_type == 'market':
                if self.check_market(annotation.description):
                    markets.append(self.check_market(annotation.description))
        return articles, dates, markets

