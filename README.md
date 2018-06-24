## TwitchNotifier for Windows
Python script which polls different Twitch streams and shows toast notification when tracked user goes live.

Reads list of stream id's from *streamlist.txt*, polls them on given intervals and shows a Windows toast notification when a stream goes live.

One stream name per line, no blank lines. Use literal id which is shown in Twitch URL when you are viewing the stream. Note that this usually is the same as display name but not necessarily.

Intervals, toast lengths etc. can be configured from *config.txt*.

Streamer list is read every time, so no need to restart when adding or removing streams.

## Installation
**Requires Python3**

Install following dependencies using pip or whatever. It is preferable to use virtual environments.
```
pip install pypiwin32 setuptools win10toast requests
```

## Running
Run using **pythonw.exe** to run in background.

```
pythonw twitchnotify_win.py

```

The script can be configured to run on startup, daemon installation script is upcoming.