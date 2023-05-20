#!/usr/bin/python3.10
# just the basic generate_text
# from https://huggingface.co/aisquared/chopt-research-125m
# pip install transformers torch
from transformers import pipeline
import torch

model_name = "aisquared/chopt-research-125m"
tokenizer_name = "aisquared/chopt-research-125m"

generate_text = pipeline(model=model_name, tokenizer=tokenizer_name, trust_remote_code=True, device=0)

if __name__ == '__main__':
    output = generate_text("Here is a greeting for the guests in our store:")
    print(output)