# Whisper Dictation

Private voice keyboard, AI chat, images, webcam, recordings, voice control in >= 4 GiB of VRAM. "The works" all AI features now running concurrently on an old laptop from 2013.

<img src="img/ss.png" alt="example pic" title="Dictation anywhere, even social media." width="300" align="right">

- Hands-free recording with `record.py`
- Speech to text conversion by `whisper.cpp`[Whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- Translate various languages
- Voice-controlled webcam, audio recorder
- Launch & control apps, with `pyautogui`
- Optional OpenAI `ChatGPT`, Google Gemini, more
- Optionally speak answers out loud with `mimic3`*
- Draw pictures with [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

**Freedoms and responsibilities** Free and open-source software comes with NO WARRANTIES. You have permission to copy and modify for individual needs in accordance with the included LICENSE.

**The ship's computer.** Inspired by the *Star Trek* television series. Talk to your computer. Have it answer back with clear, easy-to-understand speech. Network it throughout the ship. Use your voice to write Captain's Log entries when the internet is down, when satellites are busy, or in the far reaches of the galaxy, "where no man has gone before."

**Translation.** This app is optimized for dictation. It can do some translation into English. But that's not its primary task. To use it as a full-time translator, start `whisper.cpp` with `--translate` and language flags. Use `ggml-medium.bin` or larger language model in place of `ggml-tiny.en.bin`.

**Voice control.** The bot responds to commands.

Say, "Computer, on screen." A window opens up showing the webcam. Say "Computer, take a picture". A picture, "webcam/image().jpg" is saved in a 'webcam' subdirectory of the current folder. Say, "Computer, search the web for places to eat". A browser opens up with a list of local restaurants. Say, "Computer, say hello to our guest". After a brief pause, there is a reply, either from your local machine, `ChatGPT`, or a local area chat server that you set up. A voice, `mimic3` says some variation of, "Hello. Pleased to meet you. Welcome to our shop. Let me know how I can be of assistance". It's unique each time. Say, "Computer, open terminal". A terminal window pops up. Say "Computer, draw a picture of a Klingon warship". An image of a warship appears with buttons to save, print, and navigate through previously-generated images.

## New in this branch

**Fewer dependencies.** We saved over 1Gb of downloads and hours of setup by eliminating torch, pycuda, cudnn, ffmpeg dependencies. Those older versions can be found in the `legacy` branch. Get just the `main` branch to save time.

`git clone -b main --single-branch https://github.com/themanyone/whisper_dictation.git`

## Preparation

Install [GStreamer](https://gstreamer.freedesktop.org/) using the system's package manager. It is necessary to record temporary audio clips for sending to your local `whisper.cpp` speech to text (STT) server.
The required `ladspa-delay-so-delay-5s` may be found in the `gstreamer1-plugins-bad-free-extras` package.

**Fedora 42 Beta.** This OS is not a supported CUDA arch. But you can install the Fedora 41 CUDA repo from Nvidia, and it will work. But you must also install manually (from any Fedora 41 repo mirror) gcc13-13.3.1-2.fc41.1 and gcc13-c++-13.3.1-2.fc41.1 and remove compatability versions of gcc14, gcc14-c++ first. Finally, edit .bashrc to make the CUDA environment available to compile with.

Sample Fedora CUDA `.bashrc` configuration.

```shell
export CUDAHOSTCXX=g++-13
export CUDACXX="$CUDA_HOME/bin/nvcc"
export CUDA_HOME=/etc/alternatives/cuda
export CUDA_TOOLKIT_ROOT="$CUDA_HOME"
export CPLUS_INCLUDE_PATH=/usr/local/cuda/include
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:/usr/local/lib64:$HOME/.local/lib64"
export C_INCLUDE_PATH="${CUDA_HOME}/include"
export GGML_CUDA_ENABLE_UNIFIED_MEMORY=1
export CMAKE_CXX_COMPILER_LAUNCHER=ccache
# optional export LD_LIBRARY_PATH=${WHISPERCPP_ROOTDIR}/lib::$LD_LIBRARY_PATH
if ! [[ "$PATH" =~ "$HOME/.local/bin:$HOME/bin:$CUDA_HOME/bin:$CUDA_HOME/nvvm/bin" ]]; then
    PATH="$HOME/.local/bin:$HOME/bin:$CUDA_HOME/bin:$CUDA_HOME/nvvm/bin:$PATH"
fi
```

**All Linux.** Set up CUDA and gstreamer. Follow instructions from Nvidia, and your distro's website or forums.

```shell
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp

cmake -B build -DGGML_CUDA=1
cmake --build build -j6 --config Release
ln -s $(pwd)/build/bin/whisper-server ~/.local/bin/  # or just copy it it somewhere in $PATH
ln -s $(pwd)/build/bin/whisper-cli ~/.local/bin/
```

Finally, install the python requirements for this package.

```shell
cd ../whisper_dictation
pip install -r requirements.txt
```

## Quick start

```shell
whisper-server -l en -sns -m "$MODELS_DIR/ggml-tiny.en.bin" --port 7777
./whisper_cpp_client.py
```

A sound level meter appears. Adjust ambient (quiet) volume to about 33% (-33dB).  On Windows, use a modern Terminal or Powershell if ANSI escape sequences are cluttering up the output. 

## Server setup

There are many ways to start and stop `whisper-server`. There is `/etc/profile.d`, `~/.config/autostart` or launching it with a hotkey. The preferred method is to set up a user service or systemwide service. Users may save the following file as `$HOME/.config/systemd/user/whisper.service`

```shell
[Unit]
Description=Run Whisper server
Documentation=https://github.com/openai/whisper

[Service]
ExecStart=whisper-server -l en -sns -m \
 "$MODELS_DIR/ggml-tiny.en.bin" \
 --port 7777

[Install]
WantedBy=default.target
```
Run `export $MODELS_DIR=/path/to/models` (wherever the models reside). Don't forget to add that export to `.bashrc` too.

Then run `systemctl --user daemon-reload` to update the configuration. Start the service with `systemctl --user start whisper`. Make it run automatically at login with `systemctl --user enable whisper`. Check status with `systemctl --user status whisper`.

If the server and client are on the same machine, uncomment the lines `os.system("systemctl --user start whisper")` near the bottom of `whisper_cpp_client.py`. Then it will start and stop the server automatically, saving resources when not in use.

## Troubleshooting.

If `whisper-server` is slow or refuses to use VRAM when it is supposed to, reboot. Or try and reload the crashed NVIDIA uvm module `sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm`.

If VRAM is scarce, quantize `ggml-tiny.en.bin` according to whisper.cpp docs. Or use `-ng` option to avoid using VRAM altogether. It might be half as fast. But delays are not that noticeable with a modern CPU.

Edit `whisper_cpp_client.py` client to change server locations from localhost to wherever they reside on the network. You can also change the port numbers. Just make sure servers and clients are in agreement on which port to use.

Test clients and servers.

```shell
whisper-cli -l en -m $MODELS_DIR/ggml-tiny.en.bin samples/jfk.wav
./whisper-server -l en -m $MODELS_DIR/ggml-tiny.en.bin --port 7777
```

## Running an AI server

Hosting large language models provides some limited access to information, even if the internet is down. But don't trust the answers. Keep all logs and communications behind a good firewall for privacy. And network security is another topic...

Supposing any chat server will do. Many use `llama.cpp` behind the scenes. Since it is not susceptible to "pickle" code injection, we don't have to recommend special `safetensors` models. So we'll use that. Understand that this is for a local home server. Running a public server comes with a catalog of other concerns so those folks might prefer to host these in a container, and/or on somebody else's cloud.

```shell
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
```

Compilation steps are the same as for whisper.cpp, but read the docs just in case. 

### Download language models

**Finding free models.** Save hundreds on annual subscriptions by running your own AI servers for every task. Look at the [leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard) to see which models perform best in the categories you want. As a rule of thumb, quantized 7B models are about the maximum our 4GiB VRAM can handle. Search for quantized models in .gguf format, or try [the ones on our page](https://huggingface.co/hellork).

**AI Safety.** Monitor children's activities. Be aware that these models, made by the community, are under active development. They are *not guaranteed safe* for all ages.

**High VRAM usage.** Use a tool like [nvtop](https://github.com/Syllo/nvtop) (availabl from package managers) to keep an eye on available VRAM.

*Context window.* The context window is the size of input plus output. Running large models with a large context window (`-ctx` 8192), while sending graphics layers to the GPU (`-ngl` 33) for speed, uses lots of VRAM. They might even crash. With small models, it is okay to run the `llama-server` with `-ngl 33` for high speed/high memory usage. With large (> 3GiB) models, use lower values, such as `-ngl 17` and `-ctx 512`, or avoid `-ngl` altogether.

Help! [Get this project off the ground with some better hardware](https://www.paypal.com/donate/?hosted_button_id=A37BWMFG3XXFG) (PayPal donation link).

### Start chatting

```shell
./llama-server -m models/gemma-2-2b-it-q4_k_m.gguf -c 2048 -ngl 33 --port 8888
```

Use the above API endpoint by simply saying "Computer... What is the capital of France!" etc. Or navigate to its handy web interface at http://localhost:8888 and dictate into that. From there you can adjust settings like `temperature` to make it more creative, or more strict with its fact checking and self censorship.

## Give it a voice

If AI is speaking, turn volume down or relocate the mic so it doesn't interact with itself.

**Mimic3.** If you follow the instructions to configure [mimic3](https://github.com/MycroftAI/mimic3) as a service on any `linux` computer or `Raspberry Pi` on the network, Speech Dispatcher will speak answers out loud. It has an open port that other network users can use to enable speech on their devices. But they can also make it speak remotely. So it is essentially a Star Trek communicator that works over wifi. Follow the [instructions for setting up mimic3 as a Systemd Service](https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3#web-server). 

According to [this post](https://community.openconversational.ai/t/mimic-3-tts-models-failing-to-load-with-invalid-protobuf-error/15164?replies_to_post_number=6) Mimic3 has been abandoned. The author has written a new speech engine, [piper](https://github.com/rhasspy/piper), which may offer some improvements. We will try it out and see if we can use it instead.


*Developer notes.* The `mimic3-server` is already lightening-fast on CPU. Do not bother compiling it with --cuda flag, which requires old `onnxruntime-gpu` that is not compatible with CUDA 12+ and won't compile with nvcc12... We got it working! And it just hogs all of VRAM and provides no noticeable speedup.

**Female voice.** For a pleasant, female voice, use  `mimic3-download` to obtain `en_US/vctk_low` To accommodate this change, we already edited the `params` line in our `mimic3_client.py`, and commented the other line out, like so.

```
    # params = { 'text': text, "lengthScale": "0.6" }
    params = { 'text': text, "voice": "en_US/vctk_low" }
```

So just change it back if you want the default male voice, other languages, or to adjust speech characteristics to taste.

## Optional ChatGPT from OpenAI

Export the OPENAI_API_KEY and it will give preference to answers from ChatGPT. Edit `.bashrc`, or another startup file:

```shell
export OPENAI_API_KEY=<my API key>
```

We heard OpenAI also has enterprise endoints for ChatGPT that offer some privacy and security. But we have never been contacted by OpenAI and make no claims about its proprietary domains.

## Optional Google Gemini

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

The computer responds to commands. You can also call her Samantha (Or Peter with for voice).

**Mute button.** There is no mute button. Say "pause dictation" to turn off text generation. It will keep listening to commands. Say, "Thank you", "resume dictation", or "Computer, type this out" to have it start typing again. Say "stop listening" or "stop dictation" to quit the program entirely. You could also configure a button to mute your mic. Something like `bash -c 'pactl set-source-mute $(pactl get-default-source) toggle'` if your system uses `pulseaudio`.0

These actions are defined in whisper_dictation.py. See the source code for the full list. Feel free to edit them too!
0
Try saying:
- Computer, on screen. (or "start webcam"; opens a webcam window).
- Computer, take a picture. (saves to webcam/image.jpg)
- Computer, off screen. (or "stop webcam")
- Computer, record audio (records audio.mp3)
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
- Samantha, tell me about the benefits of relaxation.**
- Peter, compose a Facebook post about the sunny weather we're having.
- Stop dictation. (quits program).

# Files in this branch

`whisper_cpp_client.py`: A small and efficient Python client that connects to a running [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) server on the local machine or across the network.

`record.py`: Almost hands-free, sound-activated recorder. You can run it separately. It creates a file named `audio.wav`. Supply optional command line arguments to change the file name, quality, formats, add filters, etc. See `./record.py -h` for help. Some formats require `gst-plugins-bad` or `gst-plugins-ugly`, depending on your distribution.

The record.py `-g` option lets you insert various GStreamer plugins, mixers, filters, controllers, and effects directly into the pipeline. See the [G-streamer documentation](https://gstreamer.freedesktop.org/) for details. Many audio and video plugins are available. Run `gst-inspect-1.0` for a list. The following records a high quality, lossless audio clip with echo effect and dynamic range compression.

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

- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- Linkedin https://www.linkedin.com/in/henry-kroll-iii-93860426/
- Buy me a coffee https://buymeacoffee.com/isreality
- [TheNerdShow.com](http://thenerdshow.com/)

Copyright (C) 2024-2025 Henry Kroll III, www.thenerdshow.com.
See [LICENSE](LICENSE) for details.
