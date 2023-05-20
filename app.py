#!/usr/bin/python3.10
from transformers import pipeline
import torch
import sys

print("Loading language model. This could take a while...")
generate_text = pipeline(model="aisquared/chopt-research-125m", torch_dtype=torch.float16, trust_remote_code=True, device_map="auto")

from flask import Flask, abort, request, jsonify

app = Flask(__name__)

@app.route('/', methods=["GET","POST"])
def test():
    if request.method=='POST':
        response = {"role": "assistant", "content": ""}
        # Handle a simple prompt request
        prompt = request.form.get('prompt')
        if prompt:
            response["content"] = generate_text(prompt)
            return jsonify(response)
        
        # Handle a JSON request
        elif request.headers['Content-Type'] == 'application/json':
            data = request.get_json()
            messages = data.get('messages')
            if messages:
                # build prompt from messages history
                prompt = ""
                print("Messages received:")
                for message in messages:
                    name = message.get('name')
                    role = message.get('role')
                    content = message.get('content')
                    name = '' if name is None else name + ', '
                    prompt += f"\n{content}"
                if prompt:
                    # prompt += "Assistant:"
                    prompt = prompt.strip()
                    print("prompt:\n", prompt)
                    response["content"] = generate_text(prompt)
                    return jsonify(response)
            abort(400, 'Invalid JSON request')
    return 'Invalid request', 400

if __name__ == '__main__':
    app.run()
