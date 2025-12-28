
### The Ship's Computer:

[whisper_dictation](https://github.com/themanyone/whisper_dictation)

Interact with this model by speaking to it. Lean, fast, & private, networked speech to text, AI images, multi-modal voice chat, control apps, webcam, and sound with less than 4GiB of VRAM.

```bash
git clone -b main --single-branch https://github.com/themanyone/whisper_dictation.git
pip install -r whisper_dictation/requirements.txt

git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
GGML_CUDA=1 make -j # assuming CUDA is available. see docs
ln -s server ~/.local/bin/whisper_cpp_server # (just put it somewhere in $PATH)

whisper_cpp_server -l en -m models/ggml-tiny.en.bin --port 7777
cd whisper_dictation
./whisper_cpp_client.py
```
See [the docs](https://github.com/themanyone/whisper_dictation) for tips on integrating with llama.cpp server, enabling the computer to talk back, draw AI images, carry out voice commands, and other features.

### Install Llama.cpp via git:
