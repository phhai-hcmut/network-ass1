import logging
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import ImageTk, Image
from .rtsp_client import RTSPClient, RTSPState, InvalidMethodError
from .rtp_receiver import RTPReceiver

import time


def _parse_npt(string):
    begin, end = string.removeprefix('npt=').split('-')
    return float(begin), float(end)


class Client(tk.Tk):
    """GUI interface for RTSP client"""

    # CONTROL_BUTTONS = ["Describe", "Set up", "Play", "Pause", "Tear down"]
    PLAYBACK_BUTTONS = ["Backward", "Play", "Pause", "Forward"]
    SETUP_BUTTONS = ['Describe', "Setup", "TearDown"]
    SWITCH_BUTTONS = ['Previous', 'Next']

    def __init__(self, server_addr, server_port, rtp_port, file_name):
        super().__init__()
        self.protocol('WM_DELETE_WINDOW', self.teardown)
        self._rtsp_client = RTSPClient((server_addr, server_port))
        self.rtp_port = rtp_port
        self._rtp_recv = None
        self._video_info = {'filename': file_name}
        self.create_widgets()
        self._get_video_info()

    def create_widgets(self):
        placeholer_img = ImageTk.BitmapImage(Image.new('1', (384, 288)))
        self.image_frame = tk.Label(self, image=placeholer_img)
        self.image_frame.grid(row=0, column=0, columnspan=len(self.PLAYBACK_BUTTONS))

        for i, btn_text in enumerate(self.SWITCH_BUTTONS):
            method = btn_text.replace(" ", '').lower()
            button = tk.Button(
                self, text=btn_text, command=getattr(self, method), height=2, width=10
            )
            button.grid(row=2, column=1 + i)

        for i, btn_text in enumerate(self.PLAYBACK_BUTTONS):
            method = btn_text.replace(" ", '').lower()
            button = tk.Button(
                self, text=btn_text, command=getattr(self, method), height=2, width=10
            )
            button.grid(row=3, column=i)
        for i, btn_text in enumerate(self.SETUP_BUTTONS):
            method = btn_text.replace(" ", '').lower()
            button = tk.Button(
                self, text=btn_text, command=getattr(self, method), height=2, width=10
            )
            button.grid(row=4, column=i)

        self._video_duration = tk.StringVar(self)
        label = tk.Label(self, textvariable=self._video_duration, background='white')
        label.grid(row=2, column=3)

        self._video_remain = tk.StringVar(self)
        label = tk.Label(self, textvariable=self._video_remain, background='white')
        label.grid(row=2, column=0)

        self._video_progress = tk.DoubleVar(self, 0)
        bar = ttk.Progressbar(
            self,
            length=300,
            maximum=1,
            mode='determinate',
            orient=tk.HORIZONTAL,
            variable=self._video_progress,
        )
        bar.grid(row=1, columnspan=len(self.PLAYBACK_BUTTONS))

        self._filename = tk.StringVar(self, self._video_info['filename'])
        label = tk.Label(self, textvariable=self._filename, background='white')
        label.grid(row=5, columnspan=len(self.PLAYBACK_BUTTONS))

    def _get_video_info(self):
        self._video_info['progress'] = 0
        message = self._rtsp_client.describe(self._video_info['filename'])
        # Get total duration of the video
        range_line = next(line for line in message if line.startswith('a=range'))
        _, video_duration = _parse_npt(range_line.removeprefix('a=range:'))
        self._video_duration.set(f"Duration: {video_duration}")
        self._video_remain.set(f"Remaining: {video_duration:03}")
        self._video_info['duration'] = video_duration

        framerate_line = next(
            line for line in message if line.startswith('a=framerate')
        )
        self._video_info['frame_rate'] = float(
            framerate_line.removeprefix('a=framerate:')
        )

    def describe(self):
        message = "\n".join(self._rtsp_client.describe(self._video_info['filename']))
        if message:
            describe_frame = tk.Label(
                self, text=message, background='white', justify='left'
            )
            describe_frame.grid(row=4, column=0, columnspan=len(self.PLAYBACK_BUTTONS))

    def setup(self):
        self._rtsp_client.setup(self._video_info['filename'], self.rtp_port)
        self._rtp_recv = RTPReceiver(self.rtp_port)

    def play(self, jump=False):
        try:
            if jump:
                self._rtsp_client.play(self._video_info['progress'])
            else:
                self._rtsp_client.play()
        except InvalidMethodError:
            messagebox.showwarning("Invalid?", "Please set up video before playing")
            return

        while True:
            video_data = self._rtp_recv.read()
            if video_data:
                self.show_jpeg(video_data)
            else:
                break

    def pause(self):
        self._rtsp_client.pause()

    def teardown(self):
        is_playing = self._rtsp_client.state == RTSPState.PLAYING
        if is_playing:
            self.pause()

        if tk.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            if self._rtsp_client.state != RTSPState.INIT:
                try:  # try catch in case server dies and teardown cant process
                    self._rtsp_client.teardown()
                except:
                    pass
                self.cleanup()
            self.destroy()
            return

        if is_playing:
            self.play()

    def show_jpeg(self, video_data):
        self.image = ImageTk.PhotoImage(data=video_data)
        self.image_frame.configure(image=self.image)
        # Keep a reference to the image object
        self.image_frame.update()
        self.image_frame.image = self.image
        self._video_info['progress'] += 1 / self._video_info['frame_rate']
        remain = self._video_info['duration'] - self._video_info['progress']
        self._video_remain.set(f"Remaining: {round(remain)}")
        self._video_progress.set(self._video_info['progress'] / self._video_info['duration'])
        # if self.is_playing:
        #     self.after(round(1000 / FRAME_RATE), self.show_jpeg)

    def forward(self):
        self._video_info['progress'] += 5
        self.play(True)

    def backward(self):
        if self._video_info['progress'] > 5:
            self._video_info['progress'] -= 5
        else:
            self._video_info['progress'] = 0
        self.play(True)

    def previous(self):
        self._video_info['progress'] = 0
        self._video_info['filename'] = self._rtsp_client.switch(previous=True)
        self._filename.set(self._video_info['filename'])

    def next(self):
        self._video_info['progress'] = 0
        self._video_info['filename'] = self._rtsp_client.switch()
        self._filename.set(self._video_info['filename'])

    def cleanup(self):
        logging.info("Cleaning resources before exiting application...")
        self._rtsp_client.close()
        if self._rtp_recv is not None:
            self._rtp_recv.close()


class Client2(Client):
    """More user-friendly GUI interface for RTSP client"""

    CONTROL_BUTTONS = ["Play", "Pause", "Stop"]

    def create_widgets(self):

        placeholer_img = ImageTk.BitmapImage(Image.new('1', (384, 288)))
        self.image_frame = tk.Label(self, image=placeholer_img)
        self.image_frame.grid(row=0, column=0, columnspan=len(self.CONTROL_BUTTONS))

        for i, btn_text in enumerate(self.CONTROL_BUTTONS):
            method = btn_text.replace(" ", '').lower()
            button = tk.Button(
                self, text=btn_text, command=getattr(self, method), height=2, width=10
            )
            button.grid(row=2, column=i)
        self._video_duration = tk.StringVar()
        label = tk.Label(self, textvariable=self._video_duration, background='white')
        label.grid(row=1, column=2)

        self._video_remain = tk.StringVar()
        label = tk.Label(self, textvariable=self._video_remain, background='white')
        label.grid(row=1, column=0)

    def play(self):
        try:
            super().setup()
        except InvalidMethodError as err:
            pass
        super().play()

    def stop(self):
        super().teardown()
