"""
Pupil Capture (Pupil Labs) Network API wrapper.

Pupil Capture's clock is set to PsychoPy's core.monotonicClock on connect, so
annotation timestamps, pupil timestamps and the times logged in our CSVs share
one time base. When disabled or unreachable, every method is a no-op.
"""
from time import sleep

import msgpack
import zmq
from psychopy import core

import config


class PupilCapture:

    def __init__(self, enabled, ip, port):
        self.ip = ip
        self.connected = False
        self.recording = False
        if not enabled:
            print("Pupil Capture disabled (USE_PUPIL = False).")
            return
        try:
            self._connect(port)
            self.connected = True
            print("Connected to Pupil Capture.")
        except Exception as e:
            print(f"Pupil Capture not reachable ({e}). Continuing without pupillometry.")
            return
        try:
            print("Annotation plugin:", self._enable_annotation_plugin())
            sleep(0.5)
        except Exception as e:
            print(f"WARNING: could not auto-enable Annotation Capture ({e}). "
                  "Enable it manually in Pupil Capture > Plugin Manager.")

    def _connect(self, port):
        self.ctx = zmq.Context()
        # REQ socket for commands
        self.remote = self.ctx.socket(zmq.REQ)
        self.remote.setsockopt(zmq.RCVTIMEO, 10000)
        self.remote.setsockopt(zmq.SNDTIMEO, 10000)
        self.remote.connect(f"tcp://{self.ip}:{port}")
        # get PUB port
        self.remote.send_string("PUB_PORT")
        self.pub_port = self.remote.recv_string()
        # PUB socket for annotations
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.connect(f"tcp://{self.ip}:{self.pub_port}")
        # sync clocks
        self.remote.send_string("T " + str(core.monotonicClock.getTime()))
        self.remote.recv_string()

    def _enable_annotation_plugin(self):
        """Ask Pupil Capture to load the Annotation Capture plugin.
        Without this plugin Capture receives the annotations but does NOT write
        them into the recording (annotation.pldata)."""
        notification = {"subject": "start_plugin", "name": "Annotation_Capture", "args": {}}
        self.remote.send_string("notify.start_plugin", flags=zmq.SNDMORE)
        self.remote.send(msgpack.dumps(notification, use_bin_type=True))
        return self.remote.recv_string()

    def start_recording(self, session_name):
        if not self.connected:
            return
        # a fresh PUB socket per recording; the settle time keeps early annotations from being dropped
        self.pub.close()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.connect(f"tcp://{self.ip}:{self.pub_port}")
        sleep(1.0)
        self.remote.send_string(f"R {session_name}")
        self.remote.recv_string()
        self.recording = True
        sleep(0.25)

    def stop_recording(self):
        if not self.recording:
            return
        self.remote.send_string("r")
        self.remote.recv_string()
        self.recording = False

    def annotate(self, label, duration=config.CHORD_DURATION):
        """Send an annotation; returns its timestamp (core.monotonicClock), or None if not sent."""
        if not self.connected:
            return None
        timestamp = core.monotonicClock.getTime()
        annotation = {
            "topic": "annotation", 
            "label": label,
            "timestamp": timestamp,
            "duration": duration
        }
        try:
            self.pub.send_string(annotation["topic"], flags=zmq.SNDMORE)
            self.pub.send(msgpack.dumps(annotation, use_bin_type=True))
        except Exception as e:
            print(f"Annotation error ({label}): {e}")
            return None
        return timestamp

    def close(self):
        if not self.connected:
            return
        self.stop_recording()
        self.ctx.destroy(linger=0)
        self.connected = False
