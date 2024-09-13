# Whisper Dictation

Fast! Offline, privacy-focused, hands-free voice typing, AI voice chat, voice control, in **under 1 Gb of VRAM** when optimized for dictation alone. "The works" all AI features now running concurrently on a laptop with under 4 GiB of VRAM!

<img src="img/ss.png" alt="example pic" title="App does dictation anywhere, even social media." width="300" align="right">

- Hands-free recording with `record.py`,
- Speech to text conversion by `whisper.cpp`[Whisper.cpp](https://github.com/ggerganov/whisper.cpp),
- Translate various languages,
- Launch & control apps, with `pyautogui`,
- Optional OpenAI `ChatGPT`, Google Gemini, or custom chat server integration,
- Optionally speak answers out loud with `mimic3`.
- Draw pictures with [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui).
- Help [get us a better video card](https://www.paypal.com/donate/?hosted_button_id=A37BWMFG3XXFG) (PayPal donation link).

**Freedoms and responsibilities** Free and open-source software comes with NO WARRANTIES. You have permission to copy and modify for individual needs in accordance with the included LICENSE. Get updates from https://github.com/themanyone/whisper_dictation.git

**The ship's computer.** Inspired by the *Star Trek* television series. Talk to your computer. Have it answer back with clear, easy-to-understand speech. Network it throughout the ship. Use your voice to write Captain's Log entries when the internet is down, when satellites are busy, or in the far reaches of the galaxy, "where no man has gone before.

**Translation.** This app is optimized for dictation. It can do some translation into English. But that's not its primary task. To use it as a full-time translator, start `whisper.cpp` with `--translate` and language flags. Use `ggml-medium.bin` or larger language model in place of `ggml-tiny.en.bin`.

**Voice control.** The bot responds to commands.

For example, say, "Computer, search the web for places to eat". A browser opens up with a list of local restaurants. Say, "Computer, say hello to our guest". After a brief pause, there is a reply, either from your local machine, `ChatGPT`, or a local area chat server that you set up. A voice, `mimic3` says some variation of, "Hello. Pleased to meet you. Welcome to our shop. Let me know how I can be of assistance". It's unique each time. Say, "Computer, open terminal". A terminal window pops up. Say "Computer, draw a picture of a Klingon warship". An image of a warship appears with buttons to save, print, and navigate through previously-generated images.

## New in this branch

**Fewer dependencies.** We saved over 1Gb of downloads and hours of setup by eliminating pytorch, pycuda dependencies. Those older versions can be found in the `legacy` branch.

## Preparation

[GStreamer](https://gstreamer.freedesktop.org/) is necessary to record temporary audio clips for sending to your local `whisper.cpp` speech to text (STT) server. It should be available from various package managers.

```shell
pip install -r requirements.txt
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
GGML_CUDA=1 make -j # assuming CUDA is available. see docs
ln -s server ~/local/bin/whisper_cpp_server
```

## Quick start

```shell
whisper_cpp_server -l en -m models/ggml-tiny.en.bin --port 7777
./whisper_cpp_client.py
```

## Troubleshooting.

If VRAM is scarce, quantize `ggml-tiny.en.bin` according to whisper.cpp docs. Or use `-ng` option to avoid using VRAM altogether. It will lose some performance. But it's not that noticeable with a fast CPU.

If `whisper_cpp_server` refuses to start, reboot. Or try and reload the crashed NVIDIA uvm module `sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm`.

Edit `whisper_cpp_client.py` client to change server locations from localhost to wherever they reside on the network. You can also change the port numbers. Just make sure servers and clients are in agreement on which port to use.

Test clients and servers.

```shell
./whisper.cpp -l en -m ./models/ggml-tiny.en.bin samples/jfk.wav
ln -sf $(pwd)/main whisper_cpp
ln -sf $(pwd)/server whisper_cpp_server
./whisper_cpp_server -l en -m models/ggml-tiny.en.bin --port 7777
```

## Local chat server

Supposing any chat server will do. Many use `llama.cpp` behind the scenes, so we also use that.

```shell
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
GGML_CUDA=1 make -j # assuming CUDA is available. see docs
```

### Download language models

Save hundreds on annual subscriptions by running your own AI servers for every task. Look at the [leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard) to see which models perform best in the categories you want. As a rule of thumb, quantized 7B models are about the maximum our 4GiB VRAM can handle. Search for quantized models in .gguf format, or try [the ones on our page](https://huggingface.co/hellork).

Help [get us a better video card](https://www.paypal.com/donate/?hosted_button_id=A37BWMFG3XXFG) (PayPal donation link).

### Start chatting

```shell
./llama-server -m models/gemma-2-2b-it-q4_k_m.gguf -c 2048 -ngl 33 --port 8888
```

Use the API endpoint by simply saying "Computer... What is the capital of France!" etc. Or navigate to the handy web interface at http://localhost:8888 and dictate into that. From there you can adjust settings like `temperature` to make it more creative, or more strict with its fact checking and self censorship.

## Give it a voice

**Mimic3.** If you install [mimic3](https://github.com/MycroftAI/mimic3) as a service, the computer will speak answers out loud. Follow the [instructions for setting up mimic3 as a Systemd Service](https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3#web-server). The `mimic3-server` is already lightening-fast on CPU. Do not bother with --cuda flag, which requires old `onnxruntime-gpu` that is not compatible with CUDA 12+ and won't compile with nvcc12... We got it working! And it just hogs all of VRAM and provides no noticeable speedup.

**Female voice.** For a pleasant, female voice, use  `mimic3-download` to obtain `en_US/vctk_low` To accommodate this change, we edited the `params` line in `mimic3_client`, and commented the other line out, like so.

```
    # params = { 'text': text, "lengthScale": "0.6" }
    params = { 'text': text, "voice": "en_US/vctk_low" }
```

## Optional ChatGPT from OpenAI

Export the OPENAI_API_KEY and it will give preference to answers from ChatGPT. Edit `.bashrc`, or another startup file:

```shell
export OPENAI_API_KEY=<my API key>
```

We heard OpenAI also has enterprise endoints for ChatGPT that offer some privacy and security. But we have never been contacted by OpenAI and make no claims about its proprietary domains.

## Optional Google AI

* Sign up for a [GOOGLE_API_KEY](https://aistudio.google.com)
* `pip install -q -U google-generativeai`
* `export GENAI_KEY=<YOUR API_KEY>`

## AI Images

Now with `sdapi.py`, images may be generated locally, or across the network. Requires [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui). Start `webui.sh` on the server with --api options. Also use --medvram or --lowvram if your video is as bad as ours. If using remotely, configure our `sdapi.py` client with the server's address.

**Start stable-diffusion webui**

```shell
webui.sh --api --medvram
```

### Spoken commands and program launchers

The computer responds to commands. You can also call him Peter. (Or Samantha, if using female voice).

**Mute button.** There is no mute button. Say "pause dictation" to turn off text generation. It will keep listening to commands. Say "resume dictation", or "Computer, type this out" to have it start typing again. Say "stop listening" or "stop dictation" to quit the program entirely. You could configure a button to mute your mic, but that is no longer necessary.

These actions are defined in whisper_dictation.py. See the source code for the full list. Feel free to edit them too!

Try saying:
- Computer, on screen. (or "start webcam"; opens a webcam window).
- Computer, take a picture. (saves to /tmp/on_screen.jpg)
- Computer, off screen. (or "stop webcam")
- Computer, open terminal.
- Computer, go to [thenerdshow.com](https://thenerdshow.com/). (or any website).
- Computer, open a web browser. (opens the default homepage).
- Computer, show us a picture of a Klingon battle cruiser.
- Page up.
- Page down.
- Undo that.
- Copy that.
- Paste it.
- Pause dictation.
- Resume dictation.
- New paragraph. (also submits chat forms :)
- Peter, tell me about the benefits of relaxation.**
- Peter, compose a Facebook post about the sunny weather we're having.
- Stop dictation. (quits program).

# Files in this branch

`whisper_cpp_client.py`: A small and efficient Python client that connects to a running [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) server on the local machine or across the network.

`record.py`: Almost hands-free, sound-activated recorder. You can run it separately. It creates a file named `audio.wav`. Supply optional command line arguments to change the file name, quality, formats, add filters, etc. See `./record.py -h` for help. Some formats require `gst-plugins-bad` or `gst-plugins-ugly`, depending on your distribution.

This update provides a powerful option that lets you insert various plugins, mixers, filters, controllers, and effects directly into the GStreamer pipeline. See the [G-streamer documentation](https://gstreamer.freedesktop.org/) for details. Many audio and video plugins are available. Run `gst-inspect-1.0` for a list. The following records in a high quality, lossless format with echo effect and dynamic range compression.

`./record.py -gq 'audioecho delay=250000000 intensity=0.25 ! audiodynamic' echo.flac`

`on_screen.py` A simple python library to show and take pictures from the webcam.

`sdapi.py` The client we made to connect to a running instance of [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui). This is what gets called when you say, "Computer...Draw a picture of a horse."

Various test files, including:

`mimic3_client.py`: a client to query and test `mimic3-server` voice output servers.

`test_cuda.py`: torch, pytorch, cuda, and onnxruntime are no longer required for dictation. But you can still test them here, since `mimic3` uses onnxruntime for text to speech.

### Improvements

**Stable-Diffusion.** Stable-Diffusion normally requires upwards of 16 GiB of VRAM. But we were able to get it running with a mere 2 GiB using the `--medvram` or `--lowvram` option with [Stable Diffusion Web UI](https://techtactician.com/stable-diffusion-low-vram-memory-errors-fix/). 

**I want it to type slowly.** We would love to have it type text slowly, but typing has become unbearably-slow on sites like Twitter and Facebook. The theory is they are using JavaScript to restrict input from bots. But it is annoying for fast typists too. If occasional slow typing doesn't bother you, change the code to use `pyautogui.typewrite(t, typing_interval)` for everything, and set a `typing_interval` to whatever speed you want.

## Other Projects

Whisper Dictation is not optimized for making captions or transcripts of pre-recorded material. Use [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) or [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) for that. They too have a [server with a web interface that makes transcripts for voice recordings and videos](https://github.com/sanchit-gandhi/whisper-jax/blob/main/app/app.py). 

If you want real-time AI captions translating everyone's conversations in the room into English. If you want to watch videos with accents that are difficult to understand. Or if you just don't want to miss what the job interviewer asked you during that zoom call... WHAT???, check out my other project, [Caption Anything](https://github.com/themanyone/caption_anything). And generate captions as you record live "what you hear" from the audio monitor device (any sounds that are playing through the computer).

### Thanks for trying out Whisper Dictation!

Browse Themanyone
- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- Linkedin https://www.linkedin.com/in/henry-kroll-iii-93860426/
- [TheNerdShow.com](http://thenerdshow.com/)
