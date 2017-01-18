# -*- coding: utf-8 -*-
import re
import urllib2
import json
try:
    import boto3
except:
    pass ## not important for local development
import sys
from HTMLParser import HTMLParser

class DynamoDBConnector:

    def  __init__(self):
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table('Dictionary')

    def get(self, word):
        item = self.table.get_item(
            Key={
            'word': word
            },
            AttributesToGet=['ipa', 'audio']).get("Item")
        if item:
            return item
        else:
            raise ValueError("Word not found")

    def put(self, word, ipa, audio):
        item = self.table.put_item(
            Item={
            'word': word,
            'ipa': ipa or None,
            'audio': audio or None
            })



class WiktionaryIPAParser(HTMLParser):
    # create a subclass and override the handler methods
    foundIpaTag = False
    finished = False
    finishedIpa = False
    data = ""
    foundAudioTag = False
    foundAudio = False
    audioUrl = ""

    def handle_starttag(self, tag, attrs):
        #self.finished = self.foundAudio and self.foundIpaTag
        if self.finished:
            return
        ## IPA
        if tag == "span" and not self.finishedIpa:
            c = dict(attrs).get("class")
            if c and c == "ipa":
                self.foundIpaTag = True

        ## Audio
        if tag == "a":
            if self.foundAudioTag and not self.foundAudio:
                href = dict(attrs).get("href")
                if href and href.split('.')[-1] in ["ogg", "wav", "mp3"]:
                    if href.startswith('//'):
                        href = href[2:]
                    self.audioUrl = href
                    self.foundAudio = True
            t = dict(attrs).get("title")
            try:
                #print t
                if t and u"Hilfe:Hörbeispiel" in t:
                    self.foundAudioTag = True
            except:
                ##Bullshit
                pass


    def handle_endtag(self, tag):
        if self.finished:
            return
        if self.foundIpaTag and tag == "span":
            self.finishedIpa = True

    def handle_data(self, data):
        if self.finished:
            return
        if not self.data and self.foundIpaTag:
            self.data = data


def extract(html):
    parser = WiktionaryIPAParser()
    parser.feed(html)
    return parser.data

def parse(html):
    parser = WiktionaryIPAParser()
    parser.feed(html)
    return parser

def word2ipa(word):
    url = "https://de.wiktionary.org/w/api.php?action=parse&format=json&prop=text&page={word}".format(word=word)
    headers = { 'User-Agent' : 'paszin/german2ipa' }
    req = urllib2.Request(url, None, headers)
    data = json.loads(urllib2.urlopen(req).read())
    if data.get("error"):
        return False, word, None
    if data.get("parse"):
        parser = parse(data["parse"]["text"]["*"])
        return True, parser.data, parser.audioUrl

def removeSpecialChars(word):
    chars = "!?.-',()"
    for c in chars:
        word = word.replace(c, "")
    return word

def translate(text, dictionary):
    "translate text based on dictionary, ignore unknown words, ignore special chars"
    text = text.lower()
    for k, v in dictionary.iteritems():
        text = text.replace(k.lower(), v)
    return text
#
def lookup(word, db):
    try:
        data, success = db.get(word), True
        ipa = data.get("ipa")
        audio = data.get("audio")
    except ValueError:
        ### lookup from dynamo db
        success, ipa, audio = word2ipa(word)
    return success, ipa, audio

def lambda_handler(event, context):
    words = event.get("text")
    if not words:
        return {"error": "missing parameter text"}
    words = words.strip()
    dictionary = {}
    samples = {}
    db = DynamoDBConnector()
    wordsSet = set(map(removeSpecialChars, words.split(" ")))
    for word in wordsSet:
        success, ipa, audio = lookup(word, db)
        if not success:
            word = word.lower()
            success, ipa, audio = lookup(word, db)
        if success:
            dictionary[word] = ipa
            samples[word] = audio
            db.put(word, ipa, audio)

    return {"translation": translate(words, dictionary),
            "dictionary": dictionary,
            "samples": samples}


if __name__ == "__main__":
    print word2ipa("Test")
    sys.exit(0)
    while True:
        word = raw_input(">>>")
        success, word = word2ipa(word)
        if not success:
            print "no translation found"
        else:
            print word
