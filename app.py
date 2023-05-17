#!venv/bin/python
from transformers import pipeline
import torch
import sys

generate_text = pipeline(model="aisquared/chopt-research-125m", torch_dtype=torch.float16, trust_remote_code=True, device_map="auto")

from flask import Flask, abort, request

app = Flask(__name__)

@app.route('/', methods=["GET","POST"])
def test():
    if request.method=='POST':
        prompt = request.form.get('prompt')
        output = generate_text(prompt)
        return output
    else:
        return("ok")

if __name__ == '__main__':
    print("Start server with 'flask run'")
