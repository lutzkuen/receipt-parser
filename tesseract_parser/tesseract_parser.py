import pytesseract as pts
from pdf2image import convert_from_path
import enchant
import datetime


def is_number(in_str):
    try:
        _ = float(in_str)
        return True
    except Exception as e:
        return False


def is_decimal(i_num):
    if round(i_num) != i_num:
        return True
    else:
        return False


def clean_word(word):
    return word.replace('%', '').replace('1LYDE', 'LIDL').replace('(','').replace(')','').replace('L+DI', 'LIDL')


def blacklist(label):
    if 'steuer-nr' in label.lower():
        return False
    if 'eur*' in label.lower():
        return False
    return True


STOPWORDS = ['summe', 'visa', 'mwst', 'brutto', 'netto', 'zahlen']
MARKETS = ['drogerie', 'lidl', 'rewe', 'real', 'allguth']


class TesseractParser:
    def __init__(self, min_length=1, max_height=5, debug=False, iterations=1):
        self.min_length = min_length
        self.max_height = max_height
        self.dict_ger = enchant.Dict('de_DE')
        self.debug = debug
        self.iterations = iterations

    def parse_pdf(self, path, save_crop=False):
        pages = convert_from_path(path, 500)
        all_articles = []
        purchase_date = None
        market = None
        for page in pages:
            articles_save = []
            if not purchase_date:
                purchase_date, market = self.get_meta_information(page)
            bounding_box = (0, 0, page.size[0], page.size[1])
            _page = page
            for attempts in range(self.iterations):
                _page = _page.crop(bounding_box)
                articles, bounding_box = self.parse_page(_page)
                if len(articles) > 0:
                    articles_save = articles
                # print(articles)
            if save_crop:
                _page.save(path.replace('.pdf', '.jpg'))
            all_articles += articles_save
        if not purchase_date:
            # try to get from filename
            try:
                purchase_date = datetime.datetime.strptime(path.split('/')[-1], 'Gescannt_%Y%m%d-%H%M.pdf')
            except:
                pass
        return all_articles, purchase_date, market

    def get_meta_information(self, page):
        test_str = pts.image_to_data(page, lang='deu', config='--psm 6')
        lines = test_str.split('\n')
        purch_date = None
        purch_detail = None
        market = None
        for line in lines[1:]:
            tokens = line.split('\t')
            word = clean_word(tokens[-1])
            # try some date encodings
            for fmt in ['%d.%m.%y', '%Y-%m-%d', '%d.%m.%y %H:%M']:
                try:
                    new_purch_date = datetime.datetime.strptime(word, fmt)
                    if not purch_date:
                        purch_date = new_purch_date
                    else:
                        if new_purch_date > purch_date and new_purch_date < datetime.datetime.now():
                            purch_date = new_purch_date
                        else:
                            if new_purch_date > purch_date and new_purch_date < datetime.datetime.now():
                                purch_date = new_purch_date
                except:
                    pass
            # try some time encodings
            for fmt in ['%H:%M', '%H:%M:%S']:
                try:
                    new_purch_detail = datetime.datetime.strptime(word, fmt) - datetime.datetime(1900, 1, 1, 0, 0)
                    if not purch_detail:
                        purch_detail = new_purch_detail
                        if purch_date:
                            purch_date += purch_detail
                except:
                    pass
            if not market:
                for t_market in MARKETS:
                    if t_market in word.lower():
                        market = t_market
        return purch_date, market


    def parse_page(self, page):
        test_str = pts.image_to_data(page, lang='deu', config='--psm 6')
        lines = test_str.split('\n')
        articles = []
        total_price = 0
        price_position = 0
        line_value = ''
        line_number = 0
        block_top = 0
        block_left = 0
        valid_top = 999999
        valid_bot = 0
        valid_r = 0
        valid_l = 999999
        is_done = False
        for line in lines[1:]:
            is_valid = False
            tokens = line.split('\t')
            if not tokens[-1]:
                continue
            line_num = int(tokens[4])
            word_num = tokens[5]
            left = int(tokens[6])
            top = int(tokens[7])
            width = int(tokens[8])
            height = int(tokens[9])
            word = clean_word(tokens[-1])
            if self.debug:
                print(word)
            if is_number(word.replace(',', '.')):
                new_num = float(word.replace(',', '.'))
                if is_decimal(new_num):
                    if is_decimal(line_number):
                        if left > price_position:
                            price_position = left
                            if self.debug:
                                print(str(line_number) + ' gets replaced by ' + str(new_num))
                            line_number = new_num
                            is_valid = True
                    else:
                        line_number = new_num
                        is_valid = True
            else:
                if word.isalpha() and len(word) > self.min_length:
                    suggestions = self.dict_ger.suggest(word)
                    if len(suggestions) > 0:
                        suggestion = suggestions[0]
                    else:
                        suggestion = word
                else:
                    suggestion = word
                if suggestion.lower() in STOPWORDS:
                    # print('Stop word ' + suggestion)
                    suggestion = 'grand_total'
                    is_done = True
                    # break
                if line_value == '':
                    line_value = suggestion
                    block_top = top
                else:
                    if line_number > 0:
                        if blacklist(line_value):
                            articles.append({
                                'label': line_value,
                                'price': line_number
                            })
                        line_value = suggestion
                        line_number = 0
                        block_top = top
                        is_valid = True
                    else:
                        if block_top + self.max_height*height > top:
                            if self.debug:
                                print('Appending ' + str(suggestion))
                            line_value += ' ' + suggestion
                        else:
                            if self.debug:
                                print(line_value + ' gets replaced by ' + suggestion)
                            line_value = suggestion
                            block_top = top
            if is_valid:
                valid_top = min(valid_top, round(block_top-height))
                valid_bot = max(valid_bot, round(top+2*height))
                valid_r = max(valid_r, round(left+1.5*width))
                valid_l = min(valid_l, left-width)
            if is_done:
                if line_number > 0:
                    articles.append({
                        'label': line_value,
                        'price': line_number
                    })
                break
        # the first article is usually rubbish, hence we drop it
        return articles, (0, 0, page.size[0], valid_bot)
