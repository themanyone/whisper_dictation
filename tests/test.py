#!.venv/bin/python
# -*- coding: utf-8 -*-
import requests

# Assuming `messages` is a list of message objects
messages = [{ "role": "system", "content": "In this conversation between `user:` and `assistant:`, play the role of assistant. Reply as assistant." },
    {"role": "user", "content": "Write a sentence about a rose."},
    {"content":"A rose by any other name is still a rose.","role":"assistant"},
    {"role": "user", "content": "Say hello to my little friend."},
    {"content":"Hello, little friend.","role":"assistant"},
    {"role": "user", "content": "Describe a duck in one sentence."},
    {"content":"A duck is an aquatic shore bird.","role":"assistant"},
    {"role": "user", "content": "OMG! Tell me everything you know about ducks."},
]

payload = {
    "messages": messages
}

response = requests.post("http://localhost:5000", json=payload)
# this works, but returns the list as a string
# completion = response.text
# print(completion)
if response.status_code == 200:
    # we want data as a list object
    data = response.json()
    # data.get("content") works if "content" is optional
    # Use data["content"] to raise a KeyError if missing:
    print(data["content"])
else:
    print("Error:", response.text)
