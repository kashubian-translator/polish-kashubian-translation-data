import string
import requests
from bs4 import BeautifulSoup


suggestions_url = 'https://kaszebe.org/ajax/suggestions'
word_url_prefix = 'https://kaszebe.org/pl/'
polish_alphabet = list(string.ascii_lowercase) + ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']


def add_letter(data, letter):
    data['q'] += letter


def remove_last_letter(data):
    data['q'] = data['q'][:len(data['q']) - 1]


def fetch_translations(word):
    word_url = f"{word_url_prefix}{word}"
    response = requests.get(word_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        translations = soup.find_all('ul', class_='translations-list')
        results = []
        for ul in translations:
            results.extend([li.text.strip() for li in ul.find_all('li')])
        return results
    else:
        return ["ERROR"]


def fetch_and_save_phrases_with_translations(request_data, pl_file, csb_file):
    for letter in polish_alphabet:
        add_letter(request_data, letter)
        words_response = requests.post(suggestions_url, data=request_data)
        if len(words_response.json()) < 10:
            for word in words_response.json():
                translations = fetch_translations(word['polish'])
                for translation in translations:
                    pl_file.write(f"{word['polish']}\n")
                    csb_file.write(f"{translation}\n")
            remove_last_letter(request_data)
        else:
            fetch_and_save_phrases_with_translations(request_data, pl_file, csb_file)
            remove_last_letter(request_data)


def main():
    pl_file = open("kaszebe.pl.txt", "w")
    csb_file = open("kaszebe.csb.txt", "w")

    request_data = {
        'q': '',
        'l': 'pl',
    }

    fetch_and_save_phrases_with_translations(request_data, pl_file, csb_file)

    pl_file.close()
    csb_file.close()


main()
