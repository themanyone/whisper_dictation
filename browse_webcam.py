#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright (C) 2026 Henry Kroll III <nospam@thenerdshow.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
## MA 02110-1301, USA.
##
from flask import Flask, send_from_directory, render_template_string
import os

app = Flask(__name__)

# Set the path to your images
IMAGE_FOLDER = "webcam"
title = IMAGE_FOLDER + " gallery"


@app.route("/")
def gallery():
    image_files = [
        f for f in os.listdir(IMAGE_FOLDER) if f.endswith((".png", ".jpg", ".jpeg"))
    ]
    return render_template_string(
        """
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
    """,
        images=image_files,
        title=title,
    )


@app.route("/images/<filename>")
def image_file(filename):
    return send_from_directory(IMAGE_FOLDER, filename)


if __name__ == "__main__":
    host = "http://localhost"
    port = 9165
    print(f"{host}:{port}")
    app.run(debug=True, port=port)
