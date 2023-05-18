#!/usr/bin/python3.10
import os, sys
from urllib.parse import urlencode
# example url parsing
# params = {
    # 'name': 'John Doe',
    # 'age': 30,
    # 'city': 'New York'
# }
# query_string = urlencode(params)

def say(text):
    params = { 'text': text }
    query_string = "curl -s -X GET http://localhost:59125/api/tts?"
    query_string += urlencode(params) + "| aplay -q -"
    os.system(query_string)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        say(sys.argv[1])
    else:
        print("Import say from mimic3_client or test with `mimic3_client 'this is a test'`")
