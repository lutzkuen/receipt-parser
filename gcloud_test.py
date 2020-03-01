from gcloud_parser.gcloud_parser import GcloudParser


# PATH = '../grive/Belege/Gescannt_20200214-1743.pdf'
# PATH = '../grive/Belege/Gescannt_20200220-2026.pdf'
# PATH = '../grive/Belege/Gescannt_20200208-1357.pdf'
# PATH = '../grive/Belege/Gescannt_20200220-2026.pdf'
# PATH = '../grive/Belege/Gescannt_20200212-1926.pdf'
# PATH = '../grive/Belege/Gescannt_20200208-1357.pdf'
# PATH = '../grive/Belege/Gescannt_20200220-2025.pdf'
# PATH = '../grive/Belege/Gescannt_20200213-1940.pdf'
PATH = '../grive/Belege/Gescannt_20200228-1904.pdf'


parser = GcloudParser(debug=True)

articles, dates, markets = parser.parse_pdf(PATH)
print(articles)
print(markets)