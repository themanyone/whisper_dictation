# Whisper Dictation

Star Trek computer control via voice. ChatGPT integration. Dictation. Web search. Fast keyboard emulation using [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) and threading. https://github.com/themanyone/whisper_dictation.git

These experimental scripts are intended for working offline, on systems that have a powerful video card. For smaller, connected devices, you might want to look at whisper cloud solutions.

## Advantages and tradeoffs.

Whisper AI is currently the state of the art for open-source voice transcription software. [Whisper jax](https://github.com/sanchit-gandhi/whisper-jax) caches compiled functions to to machine code, so dictation can be responsive and fast--easily 10x as fast as other solutions. Threading allows audio recording to proceed in the background while whisper decodes speech in the foreground. The tradeoff with running Whisper-jax continuously is that a large chunk of video RAM stays reserved until shutting down this application by saying "Stop listening." Or by pressing `CTRL` - `C`. Depending on hardware and workflow, you might experience issues with other video-intensive tasks while this is running.

For a much-slower, dictation-only script, that unloads itself when not speaking, try my [voice_typing project](https://github.com/themanyone/voice_typing), which uses the bash shell to separately record and load up whisper only when spoken to. Or try my older, less-accurate [Freespeech](https://github.com/themanyone/freespeech-vr/tree/python3) project, which uses Pocketsphinx, but is very light on resources.

## Dependencies.

Go to https://github.com/google/jax#installation and follow through the steps to install cuda, cudnn, or whatever is missing. All these  [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) dependencies and video drivers can be quite bulky, requiring about 5.6GiB of downloads. Our original,[voice_typing project](https://github.com/themanyone/voice_typing) script is significantly easier on internet usage.

Do not install `torch`. It downgrades nvidia-cudnn-cu11 to an incompatible version. Then you will have to run `pip install --upgrade nvidia-cudnn-cu11`. This problem might be fixed in another update. But for now we will use conda or venv to keep things separate.

We got the commands to install jax for GPU(CUDA) [from here](https://jax.readthedocs.io/en/latest/index.html).

Install [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) and make sure the examples work.

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
git clone https://github.com/themanyone/whisper_dictation
```

There may be other dependencies not listed. Go ahead and install whatever it asks for.

```
sudo dnf install python-devel gobject-introspection-devel python3-gobject-devel cairo-gobject-devel python3-tkinter python3-devel
```

Modify `dictate.py` and set the preferred threshold audio level and device which might require some experimentation. If the microphone isn't detected, open Control Center and choose the preferred audio device for the mic, whether it is a Bluetooth, USB microphone, or whatever. You can also use `gst-inspect-1.0` to get a list of audio sources to try. The default `autoaudiosrc` should work in most cases. 

Try the examples on the [Whisper-Jax](https://github.com/openai/whisper_jax) page and make sure that is working first.

Now we are ready to try dictation.

## Usage.

```shell
cd whisper_dictation
./whisper_dictation.py
```

If it complains about missing files, modify `whisper_dictation.py` and, in the first line, set the location of Python to the one inside the virtual environment that works with Whisper-JAX. The one you installed everything in. The default for our usage is `.venv/bin/python` which should load the correct one. But if it doesn't, you can change this to the path of python inside the conda or venv environment. Then you don't have to source or activate the virtual environment. You can just run it.

Also, feel free to change the FlaxWhisperPipline language, or use "openai/whisper-large-v2" if your video card has more than the 4Gb RAM that ours does. It defaults to `openai/whisper-small.en` which hogs just over 2 gigs of video RAM. But in fact, we get *fantastic* results even with `openai/whisper-tiny.en` So you might want to go tiny instead.

### Spoken commands and program launchers.

The computer responds to commands. You can also call him Peter.

These actions are defined in whisper_dictation.py. See the source code for the full list. Feel free to edit them too!

Try saying:
- Computer, open terminal.
- Computer, open a web browser.
- Computer, search the web for places to eat.
- Page up.
- Page down.
- Undo that.
- Copy that.
- Paste it.
- New paragraph.
- Peter, tell me about the benefits of relaxation.**

** export your OPENAI_API_KEY to the environment if you want answers from ChatGPT.

```
export OPENAI_API_KEY=<my API key>
```

If you install the optional [mimic3](https://github.com/MycroftAI/mimic3), he will speak to you.

## Bonus app.

This project includes `record.py` which does hands-free recording of an mp3 audio clip from the microphone. It waits for a minimum threshold sound level of, -20dB, but you can edit the script and change that. It stops recording when audio drops below that level for a couple seconds. You can run it separately. It creates a file named `audio.mp3`. Or you can supply an output file name on the command line.

## Issues

### GPU memory usage.

According to a post by [sanchit-gandhi](https://github.com/sanchit-gandhi/whisper-jax/issues/7#issuecomment-1531124418), JAX using 90% of GPU RAM is probably unnecessary, but intended to prevent fragmentation. You can disable that with an environment variable, e.g. `XLA_PYTHON_CLIENT_PREALLOCATE=false ./whisper_dictation.py`.

You can monitor JAX memory usage with [jax-smi](https://github.com/ayaka14732/jax-smi), `nvidia-smi`, or by installing GreenWithEnvy (gwe) for Nvidia cards.

### Improvements.

Moved audio recording to the background and dictation to the foreground. Turns out spawning multiple, background threads for dictation was a bad idea. Apparently, each new `whisper-jax` instance had to be re-compiled each time. Dictation is many times faster with a single thread, runnnig in the foreground as intended.

Now using `pyperclip` and `pyautogui` to copy and paste text, instead of typing it out into the current window. The `pyautogui` module can automate everything, so this opens up the ability to add spoken commands, such as "close window."

### Issue tracker.

This is a fairly new project. There are bound to be more issues. Share them on the [issues section on GitHub](https://github.com/themanyone/whisper_dictation/issues). Or fork the project, create a new branch with proposed changes. And submit a pull request.

Thanks for trying out Whisper Dictation.

Browse Themanyone
- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- Linkedin https://www.linkedin.com/in/henry-kroll-iii-93860426/
- [TheNerdShow.com](http://thenerdshow.com/)
