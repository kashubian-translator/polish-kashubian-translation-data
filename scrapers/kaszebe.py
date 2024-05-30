import string
from time import sleep

import requests
from bs4 import BeautifulSoup


suggestions_url = 'https://kaszebe.org/ajax/suggestions'
word_url_prefix = 'https://kaszebe.org/pl/'
polish_alphabet = list(string.ascii_lowercase) + ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']


def add_letter(data, letter):
    data['q'] += letter


def remove_last_letter(data):
    data['q'] = data['q'][:len(data['q']) - 1]


def send_request(url, method, data, attempt):
    try:
        if method == 'post':
            response = requests.post(url, data=data)
        elif method == 'get':
            response = requests.get(url)
        else:
            print("Method not implemented")
            return None
        if 200 <= response.status_code < 300:
            return response
        print(f"Attempt {attempt} failed: Unsuccessful status code {response.status_code}\n"
              f"Response JSON body: {response.json()}\n")
    except requests.RequestException as e:
        print(f"Attempt {attempt} failed: Request failed: {e}\n")
    return None


def send_request_with_retries(url, method='get', data=None, retries=6, delay=10):
    for idx in range(retries):
        response = send_request(url, method, data, idx+1)
        if response is not None:
            return response
        print(f"Retrying in {delay} seconds...\n")
        sleep(delay)
    print("Maximum number of retries exceeded\n")
    return None


def fetch_translations(word):
    word_url = f"{word_url_prefix}{word}"
    response = send_request_with_retries(word_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        translations = soup.find_all('ul', class_='translations-list')
        results = []
        for ul in translations:
            results.extend([li.text.strip() for li in ul.find_all('li')])
        return results
    else:
        return ["ERROR"]


def fetch_and_save_phrases_with_translations(request_data, pl_file, csb_file, start_letter='a'):
    for letter in polish_alphabet:
        if polish_alphabet.index(letter) < polish_alphabet.index(start_letter):
            continue
        add_letter(request_data, letter)
        words_response = send_request_with_retries(suggestions_url, 'post', request_data)
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
