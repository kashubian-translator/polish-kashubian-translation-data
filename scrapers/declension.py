import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from utils import send_request_with_retries


API_URL = "https://sloworz.org/api/graphql"
POLISH_NOUN_API_URL = "https://odmiana.net/odmiana-przez-przypadki-rzeczownika-"


def fetch_polish_noun_declension(noun: str) -> dict:
    stripped_noun = noun.strip()
    quoted_noun = quote(stripped_noun)
    url = f"{POLISH_NOUN_API_URL}{quoted_noun}"
    response = requests.get(url)

    if response.status_code != 200:
        return {}

    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    declension_table = soup.find('table')

    if not declension_table:
        return {}

    declension_dict = {
        "nounVariation": {
            "nominative": "",
            "genitive": "",
            "dative": "",
            "accusative": "",
            "instrumental": "",
            "locative": "",
            "vocative": "",
            "nominativePlural": "",
            "genitivePlural": "",
            "dativePlural": "",
            "accusativePlural": "",
            "instrumentalPlural": "",
            "locativePlural": "",
            "vocativePlural": ""
        }
    }

    case_mapping = {
        'Mianownik': 'nominative',
        'Dopełniacz': 'genitive',
        'Celownik': 'dative',
        'Biernik': 'accusative',
        'Narzędnik': 'instrumental',
        'Miejscownik': 'locative',
        'Wołacz': 'vocative'
    }

    rows = declension_table.find_all('tr')[1:]  # skip header row

    for row in rows:
        cols = row.find_all('td')
        case_name = cols[0].get_text().split('(')[0].strip()
        singular = cols[1].get_text().strip()
        plural = cols[2].get_text().strip()

        if case_name in case_mapping:
            declension_dict["nounVariation"][case_mapping[case_name]] = singular
            declension_dict["nounVariation"][case_mapping[case_name] + "Plural"] = plural

    return declension_dict


def process_word(s: str) -> str:
    s = re.sub(r'\s*\(\d+\)\s*', '', s)
    s = re.sub(r'\(([^)]+)\)', r'\1', s)
    s = re.sub(r'\[([^]]+)]', r'\1', s)

    return s.strip() + '\n'


def find_kashubian_entry(pl_file, csb_file, entry_id):
    find_kashubian_entry_query = \
        f"""
        query KashubianEntry {{
          findKashubianEntry(id: {entry_id})
          {{
            word
            variation
            meanings
            {{
              id(orderBy: ASC)
              translation {{
                polish
              }}
            }}
            partOfSpeech
          }}
        }}
        """
    response = send_request_with_retries(API_URL, 'post', json={'query': find_kashubian_entry_query})
    entry = response.json()['data']['findKashubianEntry']
    meanings = entry['meanings']

    if entry['partOfSpeech'] != "NOUN":
        return

    for meaning in meanings:
        polish_translations = [part.strip() for part in meaning['translation']['polish'].split(',')]
        for translation in polish_translations:
            polish_declension_dict = fetch_polish_noun_declension(process_word(translation))
            if not polish_declension_dict:
                continue
            for declension, word in entry['variation']['nounVariation'].items():
                if not word or declension in ('nominative', 'nominativePlural'):
                    continue
                word_variations = [part.strip() for part in word.split('//')]
                for word_variation in word_variations:
                    word_variation_variations = [part.strip() for part in word_variation.split('/')]
                    for word_variation_variation in word_variation_variations:
                        csb_file.write(process_word(word_variation_variation))
                        pl_file.write(process_word(polish_declension_dict['nounVariation'][declension]))


def find_all_kashubian_entries(pl_file, csb_file, start, limit):
    find_all_kashubian_entries_query = \
        f"""
        query AllKashubianEntries {{
          findAllKashubianEntries(
            page: {{start: {start}, limit: {limit}}}
            where: {{normalizedWord: {{BY_NORMALIZED: ""}}}}
          ) {{
            select {{
              id
              normalizedWord(orderBy: ASC)
            }}
          }}
        }}
        """
    response = send_request_with_retries(API_URL, 'post', json={'query': find_all_kashubian_entries_query})
    entries = response.json()['data']['findAllKashubianEntries']['select']
    for entry in entries:
        find_kashubian_entry(pl_file, csb_file, entry['id'])
    return len(entries)


def fetch_and_save_phrases_with_translations(pl_file, csb_file, start=0, limit=500):
    entries_num = find_all_kashubian_entries(pl_file, csb_file, start, limit)
    while entries_num > 0:
        start += 1
        entries_num = find_all_kashubian_entries(pl_file, csb_file, start, limit)


def main():
    pl_file = open("../raw_data/bilingual/declension.pl.txt", "w", encoding="utf-8")
    csb_file = open("../raw_data/bilingual/declension.csb.txt", "w", encoding="utf-8")

    fetch_and_save_phrases_with_translations(pl_file, csb_file)

    pl_file.close()
    csb_file.close()


main()
