#!/usr/bin/python
from flask import Flask, send_from_directory, render_template_string
import os

app = Flask(__name__)

# Set the path to your images
IMAGE_FOLDER = 'webcam'
title = IMAGE_FOLDER + " gallery"

@app.route('/')
def gallery():
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))]
    return render_template_string('''
    <head>
        <title>{{ title }}</title>
        <style>
        body {
            background-color: #333; /* Charcoal gray */
            color: white;
            font-family: arial,verdana,helvetica,sans-serif;
        }
        </style>
    </head>
        <h1>{{ title }}</h1>
        {% for image in images %}
            <figure style="float: left; margin: 10px;">
                <img src="{{ url_for('image_file', filename=image) }}" alt="{{ image }}" style="width: 320px;"><br>
                <figcaption>{{ image }}</figcaption>
            </figure>
        {% endfor %}
    ''', images=image_files, title = title)

@app.route('/images/<filename>')
def image_file(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    host = "http://localhost"
    port = 9165
    print(f"{host}:{port}")
    app.run(debug=True, port=port)
