"""
Experiment settings. Edit these before running; every value is snapshotted
into the session's *_session.json so each data set records the settings it used.
"""
import os

# ─────────────────────────────────────────────
# FILES  (relative to this folder)
# ─────────────────────────────────────────────

STIMULI_DIR           = "stimuli"     # every *.wav is used, split in half across the two main blocks;
                                         # named <batch>_<seq>_<key>_<O|S>[_inv].wav, and two versions of
                                         # the same <batch>_<seq> never play back to back
PRACTICE_STIMULUS     = os.path.join("stimuli_others", "practice.wav")
VOLUME_CHECK_STIMULUS = os.path.join("stimuli_others", "C.wav")
OUTPUT_DIR            = "data"

# ─────────────────────────────────────────────
# MACHINE PROFILE
#   "booth":  lab computer with Pupil Capture; real sessions
#   "laptop": no eye tracker; for debugging and checking the flow
# ─────────────────────────────────────────────

MACHINE = "laptop"

FULLSCREEN = True   # False = resizable window (handy for debugging next to the console)

# TODO: update audio device for booth computer to use the speaker.
MACHINE_PROFILES = {
    "booth": {
        "USE_PUPIL":    True,
        "AUDIO_DEVICE": "Speakers (Realtek(R) Audio)",   # run PsychoPy's sound test to find the right name
        "MONITOR_NAME": "testMonitor",                   # must match a profile in PsychoPy Monitor Center
    },
    "laptop": {
        "USE_PUPIL":    False,
        "AUDIO_DEVICE": "External Headphones", 
        "MONITOR_NAME": "testMonitor",
    },
}

_profile     = MACHINE_PROFILES[MACHINE]
USE_PUPIL    = _profile["USE_PUPIL"]
AUDIO_DEVICE = _profile["AUDIO_DEVICE"]
MONITOR_NAME = _profile["MONITOR_NAME"]
AUDIO_LIB    = ["ptb", "sounddevice"]

PUPIL_CAPTURE_IP   = "127.0.0.1"
PUPIL_CAPTURE_PORT = 50020

# ─────────────────────────────────────────────
# TESTING SHORTCUTS
# ─────────────────────────────────────────────

ALLOW_SKIP = MACHINE == "laptop"   # SKIP_KEY jumps past the current page or trial; skipped answers are logged as NA
SKIP_KEY   = "right"
QUIT_KEY   = "escape"              # always active: ends the session cleanly and saves everything recorded so far

# ─────────────────────────────────────────────
# STIMULUS TIMING  (must match how the .wav files were rendered)
# ─────────────────────────────────────────────

CHORD_DURATION     = 2.4    # seconds per chord
N_COUNTDOWN_TICKS  = 4      # ticks embedded at the start of each audio file
COUNTDOWN_DURATION = 4.8    # tonic chord (2.4 s) + one bar of 4 clicks (2.4 s)

# ─────────────────────────────────────────────
# PROCEDURE
# ─────────────────────────────────────────────

BASELINE_DURATION     = 10    # seconds of the pupil baseline ("please wait" screen after the practice)
INTER_TRIAL_INTERVAL  = 0.5   # seconds of blank screen after each trial
SLIDER_SAMPLING_HZ    = 5     # continuous-rating samples per second

CONTINUOUS_SCALE_MIN   = -100
CONTINUOUS_SCALE_MAX   = 100
CONTINUOUS_SCALE_START = 0
OVERALL_SCALE          = (1, 2, 3, 4, 5, 6)

DEBUG_SLIDER = False   # True = print the continuous value every time it changes

# ─────────────────────────────────────────────
# SURVEY THEME
# ─────────────────────────────────────────────

FONT            = "Arial"
TEXT_COLOR      = "#F2F2F2"
MUTED_COLOR     = "#9A9AA0"
CARD_COLOR      = "#1C1C1F"
STRIPE_COLOR    = "#242428"
BORDER_COLOR    = "#5A5A60"
ACCENT_COLOR    = "#3B78C2"
DISABLED_COLOR  = "#4A4A4E"
ERROR_COLOR     = "#E0736B"
