#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import DEV


class Handler(FileSystemEventHandler):
    def __init__(self, fn):
        super(Handler, self).__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path.endswith(('.py',)):
            print("File has changed:%s" % event.src_path)
            self.restart()


def kill():
    global process
    if process:
        process.kill()
        process.wait()
        process = None


def start():
    global process, command
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart():
    kill()
    print("Restart process.")
    start()


def watch(path):
    observer = Observer()
    observer.schedule(Handler(restart), path, recursive=True)
    observer.start()
    start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    command = ['python3']
    if DEV:
        command.append('app.py')
    else:
        command.append('/code/app.py')

    path = os.path.abspath('.')
    watch(path)