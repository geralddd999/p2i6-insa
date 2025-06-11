import cv2, re
import argparse, logging, time,os

try:
    from picamera2 import Picamera2
    picampassed = True
except ImportError:
    picampassed = False


def tester():
    return("JPEG" in cv2.getBuildInformation())

print(tester())
