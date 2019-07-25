import logging
import os
import os.path as path
import signal
import sys
import time
from io import BytesIO
from subprocess import check_output
import glob
import json

import requests
from PIL import Image
from win10toast import ToastNotifier

# Configuration
TOAST_DURATION_SECONDS = 10
CHECK_INTERVAL_SECONDS = 3 * 60
CONFIG_READ_INTERVAL = 5
STREAMS_FILE = 'streamlist.txt'
TWITCH_API_KEY = '11ns8rulk3p89ysxwq45dmkkqvpbdv'
API_BASE_ADDRESS = 'https://api.twitch.tv/kraken/streams/{}'
TOAST_TITLE = 'Twitch stream {} is live!'
IMAGE_DIRECTORY = 'img'
DEFAULT_ICON = 'twitch.ico'
CONFIG_FILE = 'config.json'
MUTEX_FILE = 'mutex.lock'

# Setup logging
LOG_FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
LOG_FILE = 'lastrun.log'
log_format = logging.Formatter(fmt=LOG_FORMAT)
log = logging.getLogger()
log.setLevel(logging.INFO)

log_fh = logging.FileHandler(LOG_FILE, mode='a', encoding='UTF-8')
# log_sh = logging.StreamHandler(sys.stdout)
log_fh.setFormatter(log_format)
# log_sh.setFormatter(log_format)
log.addHandler(log_fh)
# log.addHandler(log_sh)

log.info('-' * 30)
log.info('Starting {}'.format(__file__))

# Cue hacky mutex-like behavior to prevent multiple processes simultaneously.
# Current PID is written to mutex file, and if mutex file exists it is checked if
# pythonw process with that pid exists. If so, then most certainly another instance is
# running. (There's a teeny tiny chance that another python process with that exact pid could
# exists,
# but that's very unlikely).
if True:
    if os.path.exists(MUTEX_FILE):
        with open(MUTEX_FILE, 'r') as f:
            mutex_pid = int(f.read())

        # Mutex check. Only one process of this script should be running at a time.
        output = check_output(['powershell.exe', '-command', '$(Get-Process pythonw).Id'])
        pids = output.decode('utf-8').split('\n')
        pids = map(lambda x: x.strip(), pids)
        pids = filter(lambda x: len(x) > 0, pids)
        pids = map(lambda x: int(x), pids)
        pids = list(pids)

        if mutex_pid in pids:
            # Process that set the mutex file still exists, another instance is (most likely)
            # running.
            # Do not allow this process to proceed.
            log.warning('Mutex indicates there\'s another instance, preventing running')
            sys.exit(0)

        # No competing process is running.
        os.remove(MUTEX_FILE)

    # Write current PID to mutex file.
    current_pid = os.getpid()

    with open(MUTEX_FILE, 'w+') as f:
        f.write(str(current_pid))

# Read config
config_exist = os.path.exists(CONFIG_FILE)
_config_counter = 0

# Create notifier
toast = ToastNotifier()


def read_config():
    global TOAST_DURATION_SECONDS, CHECK_INTERVAL_SECONDS

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except (FileNotFoundError, IOError) as e:
        log.exception('Failed to read config.txt')
        config = None

    if config is not None:
        TOAST_DURATION_SECONDS = config.get(
            'notification_duration', TOAST_DURATION_SECONDS)
        CHECK_INTERVAL_SECONDS = config.get(
            'check_interval', CHECK_INTERVAL_SECONDS)
        if not config.get('enable_logging', True):
            log.disabled = True

        log.info('Config read')


if config_exist:
    read_config()


def show_toast(title: str, msg: str, icon: str) -> None:
    '''
    Show Windows 10 Toast notification.

    :param str title: Notification title
    :param str msg: Notification message
    '''
    log.info('Showing toast with title {}'.format(title))
    # Don't interrupt another notification
    while toast.notification_active():
        time.sleep(0.5)
    # Display toast
    toast.show_toast(
        title=title,
        msg=msg,
        duration=TOAST_DURATION_SECONDS,
        icon_path=icon
    )


def get_stream_object(apikey: str, streamname: str) -> object:
    '''
    Check status for stream streamname.
    :param str apikey: Twitch API key 
    :param str streamname: Name of the stream
    :return: JSON object sent from API 
    '''
    headers = {
        'Client-ID': apikey
    }
    response = requests.get(API_BASE_ADDRESS.format(streamname), headers=headers)
    if response.ok is not True:
        log.error('Not-OK response for streamname {}'.format(streamname))
        return None
    return json.loads(response.text)


def remove_images(exceptions: list = None) -> None:
    '''
    Remove icon files except for streamers in exceptions list.
    '''
    if exceptions is None:
        exceptions = []
    image_files = []
    for ext in ['.ico']:
        image_files.extend(glob.glob('img/*' + ext))
    for image in image_files:
        if len([x for x in exceptions if x.lower() in image.lower()]) > 0:
            continue
        log.info('Removing temporary image file ' + str(image))
        os.remove(image)


def get_preview_icon(stream_name: str, stream_object: object) -> str:
    ''''
    Fetch preview icon for a streamer.

    Downloads channel logo from received URL and converts it to
    .ico file so that it can be shown in toast notification.

    :param str stream_name: Name of the stream
    :param object stream_object: Stream JSON received from Kraken
    :return: Path to the generated icon file or None
    '''

    if 'stream' not in stream_object:
        return None

    stream = stream_object['stream']
    if 'channel' not in stream:
        log.warning(
            'No channel in stream object for {}'.format(stream_name))
        return None

    preview = stream['channel']
    if 'logo' not in preview:
        log.warning(
            'Logo not available for {}'.format(stream_name))
        return None

    ico_path = path.join(IMAGE_DIRECTORY, stream_name + '.ico')
    if os.path.exists(ico_path):
        return ico_path

    small_url = preview['logo']
    response = requests.get(small_url)
    image = Image.open(BytesIO(response.content))
    image.save(ico_path)
    log.info('Downloaded icon for stream {}'.format(stream_name))

    return ico_path


def get_stream_status(stream_name: str, stream_object: object) -> dict:
    '''
    Parse the JSON received from Kraken.

    :param str stream_name: Name of the stream
    :param object streamer_object: The received JSON object
    :return dict: Dictionary having the required information about the stream
    '''

    def err(msg):
        log.warning(msg.format(stream_name))

    if stream_object is None:
        return None
    if 'stream' not in stream_object:
        err('Not stream in {}')
        return None
    stream = stream_object['stream']
    if stream is None:
        # log.info('{} is not live'.format(stream_name))
        return None
    if 'stream_type' not in stream:
        err('No stream_type in stream {}')
        return None
    if 'game' not in stream:
        err('No game in stream {}')
        return None
    if 'channel' not in stream:
        err('No channel in stream {}')
        return None
    channel = stream['channel']
    if 'status' not in channel:
        err('No status in stream {}')
        return None
    if 'display_name' not in channel:
        err('No display_name in stream {}')
        return None

    game_name = stream['game']
    channel_status = channel['status']
    stream_type = stream['stream_type']
    display_name = channel['display_name']

    # Ignore non-live streams
    if stream_type != 'live':
        return None

    log.info('Streamer {} is live!'.format(stream_name))

    try:
        icon_path = get_preview_icon(stream_name, stream_object)
    except Exception:
        log.exception('Exception while fetching stream icon')
        icon_path = None

    return {
        'game'  : game_name,
        'status': channel_status,
        'name'  : display_name,
        'icon'  : icon_path if icon_path is not None else DEFAULT_ICON
    }


def get_streamers():
    '''
    Read tracked streamers from STREAMS_FILE.
    '''
    try:
        if os.path.exists(STREAMS_FILE):
            with open(STREAMS_FILE) as f:
                return list(
                    filter(lambda x: len(x) > 0,
                           [streamer.strip() for streamer in f]
                           ))
    except Exception:
        log.exception('Got exception while reading streamers file')
        return []


if __name__ == '__main__':
    # Keep track of online streams and the games they are playing
    streamers_online = {}


    # Exit program on SIGINT
    def handle_signal(signal, frame):
        log.info('Ending program')
        os._exit(0)


    signal.signal(signal.SIGINT, handle_signal)

    try:
        # Main loop.
        while True:
            _config_counter += 1
            if _config_counter > CONFIG_READ_INTERVAL:
                read_config()
                _config_counter = 0

            # Remove temporary icons except for online streams
            remove_images(exceptions=list(streamers_online.keys()))
            streamers = get_streamers()
            show_streams = []
            log.info('Checking streamers {}'.format(streamers))
            # Enumerate tracked streamers
            for streamer in streamers:
                streamer = streamer.strip()
                if len(streamer) == 0 or streamer[0] == '#':
                    continue

                stream_obj = get_stream_object(TWITCH_API_KEY, streamer)
                stream_status = get_stream_status(streamer, stream_obj)
                # Remove ended streams
                if stream_status is None and streamer in streamers_online:
                    log.info('Streamer {} has stopped streaming'.format(streamer))
                    streamers_online.pop(streamer)
                    continue
                # Add stream status to be shown and mark the streamer as online
                if stream_status is not None and streamer not in streamers_online:
                    streamers_online[streamer] = stream_status
                    show_streams.append(stream_status)
                # Show popup if streamer changes game
                if stream_status is not None and streamer in streamers_online:
                    if streamers_online[streamer]['game'] != stream_status['game']:
                        streamers_online[streamer] = stream_status
                        show_streams.append(stream_status)
                        log.info('Streamer {} has changed game'.format(streamer))

            # Display toasts
            for streamer in show_streams:
                message = '{} playing {}\n{}'.format(
                    streamer['name'],
                    streamer['game'],
                    streamer['status']
                )
                toast_length = TOAST_DURATION_SECONDS
                log.info('Showing toast for {} seconds'.format(toast_length))
                # Note that this blocks for the duration of the toast
                show_toast(
                    TOAST_TITLE.format(streamer['name']),
                    message,
                    streamer['icon']
                )

            sleep_for = CHECK_INTERVAL_SECONDS
            log.info('Sleeping for {} seconds'.format(sleep_for))
            time.sleep(sleep_for)

    except Exception as e:
        log.error('Caught exception {}, ending program'.format(e))
else:
    log.error('Not running as __main__')

# Remove mutex file, process is shutting down.
if os.path.exist(MUTEX_FILE):
    log.info('Removing mutex file')
    os.remove(MUTEX_FILE)
