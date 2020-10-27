Streaming MJPEG over RTSP/TCP and RTP/UDP

# Server

To start the server, run the following command:
```
python3 -m server <server_port>
```

For example, if you want the server to listen on port 2000, run:
```
python3 -m server 2000
```

# Client

To start the client, run the following command:
```
python3 -m client <server_addr> <server_port> <rtp_port> <video_file>
```

For example, if you want to stream file `movie.Mjpeg` using server at
`localhost` and port 2000, receive RTP frames from port 3000, run:
```
python3 -m client localhost 2000 3000 movie.Mjpeg
```
