#!/usr/bin/python3

import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output_video')
    parser.add_argument('input_images', nargs='+')
    args = parser.parse_args()

    with open(args.output_video, 'wb') as f:
        for filename in args.input_images:
            with open(filename, 'rb') as frame:
                data = frame.read()
                f.write(len(data).to_bytes(5, 'big'))
                f.write(data)
