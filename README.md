## TwitchNotifier for Windows
Python script which polls different Twitch streams and shows toast notification when tracked user goes live or changes game.

![notification](anim.gif "Notfitication popping up when streamer goes live or changes game")

Reads list of stream id's from *streamlist.txt*, polls them on given intervals and shows a Windows toast notification when a stream goes live.

* One stream name per line
* No blank lines
* Use literal id which is shown in Twitch URL when you are viewing the stream
* Note that this usually is the same as display name but not necessarily

Polling interval can be configured from *config.json*.

Streamer list is read every time, so no need to restart when adding or removing streams.

Default polling interval is 3 minutes (180 seconds).

## Installation as scheduled task
**Requires Python3**

Open terminal in the directory with *twitchnotify_win.py*.

Create virtual environment using the following command:
```
python -m venv .
```

Install dependencies with the following command:
```
pip install pypiwin32 setuptools win10toast requests pillow
```

Open *Powershell* as *administrator*. You can do this with WindowsKey+X
and selecting "Powershell (administrator)".

Install scheduled task to run start the program on startup by running *install_uninstall.ps1*

```
.\install_uninstall.ps1
```

The scheduled task can be uninstalled by running the script again.

```
.\install_uninstall.ps1
```

## Running manually without scheduled task
Run using **pythonw.exe** to run in background.

```
pythonw twitchnotify_win.py
```
