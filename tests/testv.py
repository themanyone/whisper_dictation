#!/usr/bin/python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8087/v1", api_key="sk-xxx")
response = client.chat.completions.create(
    model="llava-phi-3",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "http://localhost:9165/images/image.jpg"
                    },
                },
                {"type": "text", "text": "Briefly caption this image."},
            ],
        }
    ],
)
print(response)
