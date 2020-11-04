from io import BytesIO
from tkinter import *
import tkinter
from PIL import Image,ImageTk
from .rtsp_client import RTSPClient
from .rtp_receiver import RTPReceiver


class Client(tkinter.Frame):
    """GUI interface for RTSP client"""
    def __init__(self, master, server_addr, server_port, rtp_port, file_name):
        self.master = master
        self.rtsp_client = RTSPClient((server_addr, server_port))
        self.rtp_port = rtp_port
        self.file_name = file_name
        self.initGUI()
    
    def initGUI(self):
        root = self.master
        root.geometry("400x380")
        frame = Frame(root)
        frame.pack()


        upper_frame = Frame(root)
        upper_frame.pack(side=TOP)
        bottom_frame = Frame(root,height=30)
        bottom_frame.pack(side=BOTTOM)

        img = ImageTk.PhotoImage(Image.new("RGB", (250,300), "gray")) #Image.open('test_img.jpg')
        panel  = Label(upper_frame, width=400,height=300, image = img)
        panel.pack(side = "bottom", expand = "no",padx=5,pady=5)
        self.image_frame = panel
        root.update()


        setup_button = Button(bottom_frame,text='Setup',command=self.setup,height = 2, width = 10)
        setup_button.pack(padx=5,pady=10,side=LEFT) 
        play_button = Button(bottom_frame,text='Play',command=self.play,height = 2, width = 10)
        play_button.pack(padx=5,pady=10,side=LEFT)
        pause_button = Button(bottom_frame,text='Pause',command=self.pause,height = 2, width = 10)
        pause_button.pack(padx=5,pady=10,side=LEFT)
        teardown_button = Button(bottom_frame, text='TearDown',command=self.teardown,height = 2, width = 10)
        teardown_button.pack(padx=5,pady=10,side=LEFT)

    def setup(self):
        self.rtsp_client.setup(self.file_name,self.rtp_port)
        self.rtp_recv = RTPReceiver(self.rtp_port)
        pass

    def play(self):
        self.rtsp_client.play()

        while True:
            video_data = self.rtp_recv.get_data()
            if video_data == '': break
            else: self.show_jpeg(video_data)
    def pause(self):
        self.rtsp_client.pause()
        #when this happens the client socket will just timeout and stop, no big deal.

    def teardown(self):
        self.rtsp_client.teardown()
        self.master.destroy()

    def show_jpeg(self, video_data):
        im = Image.open(BytesIO(video_data))
        image = ImageTk.PhotoImage(im)
        self.image_frame.configure(image=image)
        self.image_frame.image = image
        self.master.update()
        

        

