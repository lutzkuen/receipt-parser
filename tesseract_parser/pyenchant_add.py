import sys
import enchant

if __name__ == '__main__':
    new_word = sys.argv[1]
    d_ger = enchant.Dict('de_DE')
    d_ger.add(new_word)