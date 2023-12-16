# Whisper Dictation

Fast! Offline, privacy-focused, hands-free voice typing, AI voice chat, voice control, in **under 1 Gb of VRAM** when optimised for dictation alone. "The works" all AI features now running concurrently on a laptop with under 4GiB of VRAM!

<img src="img/ss.png" alt="example pic" title="App does dictation anywhere, even social media." width="300" align="right">

- Listens and types quickly with `whisper-jax` or `whisper.cpp`,
- Hands-free, text appears under mouse cursor,
- Translates other languages into English,
- Launches & controls apps, with `pyautogui`,
- Optionally communicates with OpenAI `ChatGPT` or an included chat server.
- Optionally speaks answers out loud with `mimic3`.
- Draws pictures with stable-diffusion-webui.
- Client and server versions included.

Get it from https://github.com/themanyone/whisper_dictation.git

**The ship's computer.** Inspired by the *Star Trek* television series. Talk to your computer any time. And have it answer back with clear, easy-to-understand speech. Network it throughout the ship. Use your voice to write Captain's Log entries when the internet is down, when satellites are busy, or in the far reaches of the galaxy, "where no man has gone before."

**Privacy focused.** Most voice keyboards, dictation, translation, and chat bots depend on sending data to remote servers, which is a privacy concern. Keep data off the internet and confidential with your own, local servers. A CUDA-enabled video card with at least 1Gb is all that's needed to run an uncensored virtual assistant that listens and responds via voice. While being completely free, offline, and independent.

**Dictation.** Start speaking and whatever you say will be pasted into the current window. This project now uses a client-server model. So other network users may use it without installing all these dependencies.

**Translation.** This app is optimised for dictation. It can do some translation into English. But that's not its primary task. To use it as a full-time translator, start whisper.cpp with `--translate` flag and use ggml-medium.bin or larger language model in place of ggml-small.en.bin.

Or if using JAX, set `task="transcribe"` to `task="translate"` inside `whisper_dictation.py`, and, if there is enough VRAM, choose a larger model for the pipeline, such as `openai/whisper-large-v2` for improved translation results.

**Voice control.** The bot also responds to commands.

For example, say, "Computer, search the web for places to eat". A browser opens up with a list of local restaurants. Say, "Computer, say hello to our guest". After a brief pause, there is a reply, either from `ChatGPT`, the included chat server on the local machine, or another, networked chat server that you set up. A voice, `mimic3` says some variation of, "Hello. Pleased to meet you. Welcome to our shop. Let me know how I can be of assistance". It's unique each time. Say, "Computer, open terminal". A terminal window pops up. Say "Computer, draw a picture of a Klingon warship". An image of a warship appears with buttons to save, print, and navigate through previously-generated images.

**AI Images.** Now with the included stable-diffusion API, `sdapi.py`, images may be generated locally, or across the network. Requires [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui). Start `webui.sh` on the server with --medvram and --api options. If using remotely, configure our `sdapi.py` client with the server's address.

**Chat.** You can converse with our own chat bot now. Start it with `flask run` whisper_dictation will use that. There is no need to say its name except to start the conversation. From then on it goes into a conversational mode. Say "Resume dictation" to start typing again.

Set the chat language model in `app.py`. The first time you use it, it will download the language model from huggingface. Our chat implementation keeps track of the current chat session only. The conversation is stored in RAM, and simply discarded after the program exits. It is never saved to the cloud, or made available to the Galactic Federation for the authorities at Star Fleet to go over with a fine-toothed comb...

## Advantages and tradeoffs.

**Whisper JAX or Whisper.cpp?** Whisper AI is currently the state of the art for open-source Python voice transcription software. [Whisper JAX](https://github.com/sanchit-gandhi/whisper-jax) accelerates Whisper AI with optimised JAX code. [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) takes a different route, and rewrites Whisper AI in bare-metal C++, so it might yield even better performance on some accelerated hardware. And, if you already have C++ development libraries, video drivers, tools, and experience, C++ eliminates having to download the roughly 5 GiB of Python dependencies for Whisper JAX.

Our implementation may be adapted to use any back-end implimentation of Whisper AI. All we do is record audio when sound (hopefully speech) is detected. We send the audio to a `whsper-jax` or [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) server to translate the audio into text.

The tradeoff with running Whisper continuously is that some VRAM stays reserved until shutting down the stand-alone application or server. Depending on hardware and workflow, you might experience issues with other video-intensive tasks, games mostly, while these things are running.

**Time limits.** Our voice detection listens for 10 minutes before it gets bored and signs off. It then waits an additional 10 minutes for some type of acknowledgement or grunt before shutting down the client and freeing resources. Feel free to change the recording duration in `record.py`. Be aware that longer recordings use additional /tmp space, which usually resides in RAM.

For an extremely-simple, light-weight, dictation-only client/server solution, try the [voice_typing](https://github.com/themanyone/voice_typing) app. It uses the bash shell to record and loads up whisper only when spoken-to. It now has a `whisper.cpp` client too. Or try the ancient, less-accurate [Freespeech](https://github.com/themanyone/freespeech-vr/tree/python3) project, which uses old-school Pocketsphinx, but is very light on resources.

Whisper Dictation is not optimised for making captions or transcripts of pre-recorded material. Use [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) or [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) for that. They too have a [server with a web interface that makes transcripts for voice recordings and videos](https://github.com/sanchit-gandhi/whisper-jax/blob/main/app/app.py). If you want real-time AI captions translating everyone's conversations in the room into English. If you want to watch videos with accents that are difficult to understand. Or if you just don't want to miss what the job interviewer asked you during that zoom call... WHAT???, check out my other project, [Caption Anything](https://github.com/themanyone/caption_anything). And generate captions as you record live "what you hear" from the audio monitor device (any sounds that are playing through the computer).

## Whisper.cpp Client

We will need a few dependencies to get the `whisper.cpp` client running.

```shell
pip install ffmpeg
pip install pyautogui
pip install pyperclip
pip install pygobject
```

Now edit `whisper_cpp.py`  and set the address of cpp_url to the address of your server machine. In this case, it is already set up to use localhost.

`cpp_url = "http://127.0.0.1:8080/inference"`

## Whisper.cpp Server

Compile [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) with some type of acceleration for best results. We are using cuBLAS.

We had to had to modify `Makefile` to get it to compile:
	`NVCCFLAGS = -allow-unsupported-compiler ...`

To minimize GPU footprint, launch `server` with tiny.en model. It uses just over 111 MiB VRAM on our budget laptop. `--convert` is required because we record in .mp3 format.

```shell
./server -l en -m models/ggml-tiny.en.bin --convert
```

Due to a [bug](https://github.com/ggerganov/whisper.cpp/issues/1587), it may be necessary to add the `-ng` flag but it does not seem to affect our performance with cuBLAS.

Edit `whisper_cpp.py` clients to change the server location from localhost to wherever the server resides on the network.

**Start a client.**

```shell
cd whisper_dictation
./whisper_cpp.py
```

**Optionally start a chat server.**

```shell
flask run
```

**Optionally start stable-diffusion webui**

```shell
webui.sh --api --medvram
```

Control your computer. Refer to the section on [spoken commands and program launchers](#Spoken).

## Whisper-JAX Setup.

If `whisper.cpp` server does not work, or to compare back ends, we can also connect to Whisper-JAX.

Go to https://github.com/google/jax#installation and follow through the steps to install cuda, cudnn, or whatever is missing. All these [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) dependencies and video drivers can be quite bulky, requiring about 5.6GiB of downloads.

```shell
sudo dnf install python-devel gobject-introspection-devel python3-gobject-devel cairo-gobject-devel python3-tkinter python3-devel
```

Install `torch` for the chat server. But do not install it in the same conda or venv virtual environment as `whisper_dictation`. Or use your main python installation. If you install `torch` in the same virtual environment, it could downgrade `nvidia-cudnn-cu11` to an incompatible version. Then you will have to run something like `./.venv/bin/python -m pip install --upgrade nvidia-cudnn-cu11` from within the virtual environment to make `whisper-jax` work again. This difficulty might be addressed in another update. Or you can try building `torch` from source. But for now it's much easier to use conda or venv to keep things separate.

The commands to install JAX for GPU(CUDA) are copied [from here](https://jax.readthedocs.io/en/latest/index.html).

Install [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) and make sure the examples work. You may need to reboot to make CUDA work, after getting everything installed. And after each kernel update, and video driver upgrade/recompilation. Update: An alternative to rebooting is to reload the Nvidia uvm module `sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm`.

```shell
# activate conda or venv
python3 -m venv .venv
source .venv/bin/activate
# install dependencies
pip install  nvidia-cudnn-cu11
pip install "jax[cuda]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
pip install numpy
pip install ffmpeg
pip install pyautogui
pip install pyperclip
pip install pygobject
```

There may be other dependencies. Look in requirements.txt.

Modify `dictate.py` and set the preferred threshold audio level and device. This could require experimentation. If the microphone is not detected, open Control Center or Volume Control settings. And choose the preferred audio device for the mic, whether it is a Bluetooth, USB microphone, or whatever. You can also use `gst-inspect-1.0` to get a list of audio sources to try. The default `autoaudiosrc` should work in most cases. 

Again, explore the examples on the [Whisper-Jax](https://github.com/sanchit-gandhi/whisper-jax) page and make sure whisper is working first. Edit `whisper_dictation.py` to use the preferred pipeline and dictation model from their examples for best results. We found that `jnp.bfloat16` is for TPU devices. So `jnp.float16` is what we use for our laptop GPU. Those with a decent, desktop GPU might prefer float32. Reference, [PyTorch docs.](https://pytorch.org/xla/release/2.1/index.html)

Now we are ready to try dictation.

## Usage.

```shell
cd whisper_dictation
./whisper_dictation.py
```

Refer to the section on [GPU memory usage](#Issues).

If it complains about missing files, modify `whisper_dictation.py` and, in the first line, set the location of Python to the one inside the virtual environment that works with Whisper-JAX. The one you installed everything in. The default for our usage is `.venv/bin/python` which should load the correct one. But if it doesn't, you can change this to the path of python inside the conda or venv environment. Then you don't have to source or activate the virtual environment each time. You can just change to the directory and run it.

Feel free to change the FlaxWhisperPipline language, or use "openai/whisper-large-v2" if your video card can afford having more than 1Gb VRAM tied-up. It defaults to `openai/whisper-small.en` which uses around 975MiB VRAM when [optimised for size](#Issues). But in fact, we get *fantastic* results even with `openai/whisper-tiny.en` So you might want to go tiny instead. Then it might even work with a tiny video card. We would be interested to know.

### Spoken commands and program launchers.

The computer responds to commands. You can also call him Peter.

**Mute button.** There is no mute button. Say "pause dictation" to turn off text generation. It will keep listening to commands. Say "resume dictation", or "Computer, type this out" to have it start typing again. Say "stop listening" or "stop dictation" to quit the program entirely. You could configure a button to mute your mic, but that is no longer necessary and beyond the scope of this program.

These actions are defined in whisper_dictation.py. See the source code for the full list. Feel free to edit them too!

Try saying:
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

** export your OPENAI_API_KEY to the environment if you want answers from ChatGPT. If your firm is worried about privacy and security, use the local chat bot with `flask run`. ChatGPT also has an enterprise version that they claim to be more private and secure. We are not affiliated with OpenAI, and therefor do not receive referral benefits.

### Optional chat and text-to-speech.

```shell
# in another terminal, not using the .venv reserved for whisper_dictation
pip install "accelerate>=0.16.0,<1" "transformers[torch]>=4.28.1,<5" "torch>=1.13.1,<2"
cd whisper_dictation
flask run
```

```shell
export OPENAI_API_KEY=<my API key>
```

If there is no API key, or if ChatGPT is busy, it will ping a private language model running on http://localhost:5000. There are language models on [huggingface](https://huggingface.co/models) that produce intelligible conversation with 1 Gb of video RAM. So now whisper_dictation has its own, privacy-focused chat bot. The default language model is for research only. It's pretty limited to fit into such limited space, but rather chatty. He seems to excel at writing poetry, but is lacking in factual information. It is recommended that you edit `app.py` and choose a larger language model if your system supports it.

**Mimic3.** If you install [mimic3](https://github.com/MycroftAI/mimic3) as a service, the computer will speak answers out loud. Follow the [instructions for setting up mimic3 as a Systemd Service](https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3#web-server). The `mimic3-server` is already lightening-fast on CPU. Do not bother with --cuda flag, which requires old `onnxruntime-gpu` that is not compatible with CUDA 12+ and won't compile with nvcc12... We got it working! And it just hogs all of VRAM and provides no noticeable speedup anyway. Regular `onnxruntime` works fine with mimic3.

**Female voice.** For a pleasant, female voice, use  `mimic3-download` to obtain `en_US/vctk_low` and change the `params` line in `mimic3_client`, commenting the other line out, like so:

```
    # params = { 'text': text, "lengthScale": "0.6" }
    params = { 'text': text, "voice": "en_US/vctk_low" }
```

## File listing.

`whisper_cpp.py`: A small and efficient Python client that connects to a running [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) server on the local machine or across the network.

`whisper_dictation.py`: A stand-alone app bundled with Whisper-JAX Python. (No server required.) It loads the language model and takes a long time to start up. It also uses more VRAM (adjustable with environment variables. See JAX documentation). But with those extra resources it might be more responsive than client/server solutions.

`whisper_client.py`: A client version of Whisper Dictation. The client connects to a local [Whisper JAX server](https://jserver.py) running on the machine, the local network, or the internet. Edit `whisper_client.py` to configure the server location. Clients make dictation available even on budget laptops and old phones that can run linux/python from the app store.

`jserver.py`: A `whisper-jax` server. Run it with `venv-run jserver.py`. You might also find that, although they start quickly, clients are slightly less-responsive, compared to the bundled version. This is because servers set aside extra resoures to handle multiple clients, resources which typically aren't necessary for one user. If only a handful of clients will use it, editing `jserver.py` in certain ways may speed it up somewhat. Make it use the "openai/whisper-tiny.en" checkpoint. Reduce BATCH_SIZE, CHUNK_LENGTH_S, NUM_PROC to the minimum necessary to support your needs.

`record.py`: hands-free recording from the microphone. It waits up to 10 minutes listening for a minimum threshold sound level of, -20dB, but you can edit the script and change that. It stops recording when audio drops below that level for a couple seconds. You can run it separately. It creates a cropped audio soundbite named `audio.mp3`. Or you can supply an output file name on the command line.

`app.py`: A local, privacy-focused AI chat server. Start it by typing `flask run` from within the directory where it resides. You can use almost any chat model on huggingface with it. Edit the file, and and change the model configuration. It is not a security-focused server, however. So beware using it outside the local network. And do not share its address with more than a few friends. In particular, flask apps have no built-in protection against distributed denial-of-service attacks (DDoS).

Various test files, including:

`mimic3_client.py`: a client to query and test `mimic3-server` voice output servers.

`test_cuda.py`: test your torch, pytorch, cuda, and optional onnxruntime installation

### Improvements.

**Stable-Diffusion.** Stable-Diffusion normally requires upwards of 16Gb of VRAM. But we were able to get it running with a mere 2Gb using the `--medvram` option with [The Stable Diffuion Web UI](https://techtactician.com/stable-diffusion-low-vram-memory-errors-fix/). 

**Text goes to wrong place.** We now use `pyperclip` and `pyautogui` to paste text, instead of typing responses into the current window. We use middle-click paste on Linux, so that it also works in terminals. If you miss and it doesn't put text where you want, you can always manually middle-click it somewhere else.

**Fixing Linux paste.** "No. I don't want to use middle-click on Linux!" The alternative to using middle click on Linux is to change the behavior of the Linux terminal. Are you tired of having to remember to use Ctrl-Shift-C and Ctrl-Shift-V in the terminal, instead of Ctrl-C and Ctrl-V? The beauty of Linux is being able to customize. So let's do it!

[Modifying Terminal Settings](https://askubuntu.com/questions/53688/making-ctrlc-copy-text-in-gnome-terminal)

    Open your terminal emulator (e.g., gnome-terminal, xterm, etc.).
    Go to the terminal's menu and select "Edit" or "Preferences".
    Look for the "Shortcuts" or "Keyboard" section.
    Find the entry for "Copy" or "Interrupt" and modify the keybinding from CTRL-Shift-C to CTRL-C. Do the same for CTRL-Shift-V, changing it to CTRL-V.
    The interrupt or "stop script" hotkey will automatically be remapped from CTRL-C to Ctrl-Shift-C.
        Note: The exact steps may vary depending on your terminal emulator. Refer to the above link or help resources specific to your terminal emulator for more information.

By following these steps, you will have swapped the behavior of the "break" or "stop script" Ctrl-C, and the copy, Ctrl-Shift-C hotkeys in the Linux terminal.

Now we are ready to change `whisper_cpp.py`, `whisper_dictation.py` or `whisper_client.py` to use Ctrl-V paste instead of middle click. Somewhere around line 144, change the line that says `pyautogui.middleClick()` to `pyautogui.hotkey('ctrl', 'v')`.

**I want it to type slowly.** We would love to have it type text slowly, but typing has become unbearably-slow on sites like Twitter and Facebook. The theory is they are using JavaScript to restrict input from bots. But it is annoying as hell to fast typists too. If you enjoy watching the sunset while it types one, letter, at, a, time on social media, you can change the code to use `pyautogui.typewrite(t, typing_interval)` for everything, and set a `typing_interval` to whatever speed you want.

## JAX Issues.

**GPU memory usage.** According to [JAX documentation](https://jax.readthedocs.io/en/latest/gpu_memory_allocation.html), JAX preallocates around 75% of VRAM to reduce allocation overhead and memory fragmentation. Configure JAX GPU usage through environment variables to save space.

`export XLA_PYTHON_CLIENT_ALLOCATOR=platform` provides the smallest GPU footprint, 983MiB with `openai/whisper-small.en`. We noticed no performance penalty, and no memory fragmentation with this setting. Because Whisper Dictation only uses one compiled JAX process, and reuses it each time. Put in `~/.bashrc` or `~/.bash_profile` to make changes persistent.

If the above setting causes problems, try the following.

`export XLA_PYTHON_CLIENT_PREALLOCATE=false` This uses around 2048MiB of VRAM. We did not notice *any* performance boost preallocating half of our laptop's VRAM. But mileage may vary.

`export XLA_PYTHON_CLIENT_MEM_FRACTION=.XX` If the above preallocation is enabled, this makes JAX preallocate XX% of the total GPU memory, instead of the default 75%.

Monitor JAX memory usage with [jax-smi](https://github.com/ayaka14732/jax-smi), `nvidia-smi`, or by installing the bloated, GreenWithEnvy (gwe) from Nvidia that does the exact-same thing with a graphical interface.

This is a fairly new project. There are bound to be more issues. Share them on the [issues section on GitHub](https://github.com/themanyone/whisper_dictation/issues). Or fork the project, create a new branch with proposed changes. And submit a pull request.

### Thanks for trying out Whisper Dictation!

Browse Themanyone
- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- Linkedin https://www.linkedin.com/in/henry-kroll-iii-93860426/
- [TheNerdShow.com](http://thenerdshow.com/)
