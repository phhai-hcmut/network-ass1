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
        root.geometry("400x400")
        frame = Frame(root)
        frame.pack()


        upper_frame = Frame(root)
        upper_frame.pack(side=TOP)
        bottom_frame = Frame(root)
        bottom_frame.pack(side=BOTTOM)

        img = ImageTk.PhotoImage(Image.new("RGB", (300,300), "gray")) #Image.open('test_img.jpg')
        panel  = Label(upper_frame, width=350,height=350, image = img)
        panel.pack(side = "bottom", expand = "no",padx=5,pady=5)
        self.image_frame = panel
        root.update()


        setup_button = Button(bottom_frame,text='Setup',command=self.setup)
        setup_button.pack(padx=5,pady=10,side=LEFT)
        play_button = Button(bottom_frame,text='Play',command=self.play)
        play_button.pack(padx=5,pady=10,side=LEFT)
        pause_button = Button(bottom_frame,text='Pause',command=self.pause)
        pause_button.pack(padx=5,pady=10,side=LEFT)
        teardown_button = Button(bottom_frame, text='TearDown',command=self.teardown)
        teardown_button.pack(padx=5,pady=10,side=LEFT)

    def setup(self):
        self.rtsp_client.setup(self.file_name,self.rtp_port)
        self.rtp_recv = RTPReceiver(self.rtp_port)
        pass

    def play(self):
        self.rtsp_client.play()

        video_data = self.rtp_recv.get_data()
        print('Data:', video_data[0:15])
        while video_data != '':
            print('received vid data')
            self.show_jpeg(video_data)
    def pause(self):
        self.rtsp_client.pause()
    def teardown(self):
        self.rtsp_client.teardown()

    def show_jpeg(self, video_data):
        print('printin')
        im = Image.open(BytesIO(video_data))
        image = ImageTk.PhotoImage(im)
        self.image_frame.configure(image=image)
        self.image_frame.image = image
        self.master.update()

        

