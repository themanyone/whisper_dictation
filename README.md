# Whisper Dictation

Fast, keyboard-emulated dictation for Linux with using [whisper-jax](https://github.com/sanchit-gandhi/whisper-jax) and threading. https://github.com/themanyone/whisper_dictation.git

These experimental scripts are intended for working offline, on systems that have a powerful video card. For smaller, connected devices, you might want to look at whisper cloud solutions.

## Advantages and tradeoffs.

Whisper AI is currently the state of the art for open-source voice transcription software. With this app, [Whisper](https://github.com/openai/whisper) does not have to load up each time you speak, so dictation can be responsive and fast. Threading enables you to continue speaking while it is still decoding your last sentence. The tradeoff with running Whisper-jax continuously in the background is that a large chunk of video RAM stays reserved until shutting down this application. Depending on hardware and workflow, you might experience issues with other video-intensive tasks while this is running.

For slower continuous dictation that unloads itself when not speaking, try my [voice_typing project](https://github.com/themanyone/voice_typing), which uses the bash shell to separately record and load up whisper only when spoken to. Or try my older, much less-accurate [Freespeech](https://github.com/themanyone/freespeech-vr/tree/python3) project, which uses Pocketsphinx, but is very light on resources.

## Downloading and using.

```shell
# activate conda or venv
# Can be anywhere you want to install whisper-jax, and everythnig under
conda activate /opt/conda

# install dependencies
# get whisper-jax working before continuing with this project
pip install --upgrade --no-deps --force-reinstall git+https://github.com/sanchit-gandhi/whisper-jax.git
pip install numpy
pip install ffmpeg
# for record.py
pip install pygobject
git clone https://github.com/themanyone/whisper_dictation
```

There may be other dependencies not listed, such as `xdotool`. Go ahead and install whatever it asks for.

```
sudo dnf install python-devel gobject-introspection-devel python3-gobject-devel cairo-gobject-devel
```

Modify `dictate.py` and set your threshold audio level and device. Use `gst-inspect-1.0` to get a list of sources. The default `autoaudiosrc` should work in most cases.

If it complains about missing files, modify `whisper_dictation.py` and, in the first line, set the location of Python to the one inside the virtual environment works with Whisper-JAX. The one you installed everything in. The default for our usage is `/usr/bin/env python` which should load the one the current environment is using. But if you set this to the version of python inside the conda or venv environment, then you don't have to source or activate the virtual environment. You can just run it.

Also feel free to change the FlaxWhisperPipline to change the language, or use "openai/whisper-large-v2" if your video card has more than the 4Gb RAM that ours does.

Try the examples on the [Whisper-Jax](https://github.com/openai/whisper_jax) page and make sure that is working first.

Now we are ready to try a dictation.

```shell
cd whisper_dictation
./whisper_dictation.py
```

## Bonus app.

This project includes `record.py` which does hands-free recording of an mp3 audio clip from the microphone. It waits for audio of a certain level, usually -20dB, and quits when audio drops below that level for a couple seconds. You can run it separately. It creates a file named `audio.mp3`. Or you can supply an output file name on the command line.

## Issues

### GPU memory usage.

According to a post by [sanchit-gandhi](https://github.com/sanchit-gandhi/whisper-jax/issues/7#issuecomment-1531124418), JAX using 90% of GPU RAM is probably unnecessary, but intended to prevent fragmentation. You can disable that with an environment variable, e.g. `XLA_PYTHON_CLIENT_PREALLOCATE=false ./whisper_dictation.py`.

You can monitor JAX memory usage with [jax-smi](https://github.com/ayaka14732/jax-smi) or by installing GreenWithEnvy (gwe) for Nvidia cards.

### Race conditions.

Currently, there are problems where text is recognized or typed out-of-order. A queue solution has been worked-out as a milestone and is being tested on the `queue` branch if you want to contribute. It should be ready by May 10th.

### Issue tracker.

This is a fairly new project. There are bound to be more issues. Share them on the [issues section on GitHub](https://github.com/themanyone/whisper_dictation/issues). Or fork the project, create a new branch with proposed changes. And submit a pull request.

Thanks for trying out Whisper Dictation.

Browse Themanyone
- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- Linkedin https://www.linkedin.com/in/henry-kroll-iii-93860426/
- [TheNerdShow.com](http://thenerdshow.com/)