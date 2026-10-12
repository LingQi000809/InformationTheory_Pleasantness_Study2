"""
Chord Pleasantness Experiment
------------------------------
PsychoPy experiment for in-person study of chord pleasantness ratings
with Pupil Labs (Pupil Capture) pupillometry integration.

Structure per trial:
  1. Audio file plays (includes 4-tick countdown + 20 chords at 2.4s each)
  2. Continuous pleasantness slider active throughout (advance LOCKED until audio ends)
  3. ZMQ annotations sent to Pupil Capture at each chord onset (after countdown)
  4. After audio: overall pleasantness rating (1-6)
  5. After that: overall arousal rating (1-6)  <-- NEW addition
  6. Repeat for 32 trials

After all trials:
  - Demographics (Gold-MSI / BMRQ typically delivered via Qualtrics)

Requirements:
  pip install pyzmq

Pupil Capture must be running before the experiment starts.
Set PUPIL_CAPTURE_IP below if Pupil Capture is on a different machine.

Monitor setup:
  Before running, open PsychoPy Monitor Center and create/confirm a monitor
  profile named 'testMonitor' with your screen's physical dimensions and
  resolution. PsychoPy handles all scaling automatically from there.
"""

from psychopy import visual, core, event, sound, gui, monitors
import zmq
import csv
import random
from datetime import datetime
import os
os.chdir(os.path.dirname(os.path.abspath(__file__))) #sets dir to THIS
from time import sleep
import msgpack
from psychopy import prefs
# comment out when not at home!!!!!
prefs.hardware['audioDevice'] = 'MacBook Pro Speakers' # for testing!!!!!

# ─────────────────────────────────────────────
# CONFIGURATION — edit these before running
# ─────────────────────────────────────────────

STIMULI_DIR  = "Ling_orig_study1_stimuli_wav"          # folder containing your 32 .wav audio files
STIMULI_CSV  = "stimuli_list_study1_Testonly.csv"      # TESTING!!XXX CSV with columns: filename, trial_id
OUTPUT_DIR   = "data"                                  # folder where output CSVs will be saved

MONITOR_NAME = "testMonitor"      # must match a profile in PsychoPy Monitor Center

CHORD_DURATION      = 2.4         # seconds per chord
N_COUNTDOWN_TICKS   = 4           # ticks embedded at start of each audio file
COUNTDOWN_DURATION = 4.8          # tonic chord (2.4s) + one bar of 4 clicks (2.4s)
N_CHORDS_PER_TRIAL  = 11          # chords per sequence (after countdown) #UPDATE!

PUPIL_CAPTURE_IP    = "127.0.0.1" # change if Pupil Capture is on another machine
PUPIL_CAPTURE_PORT  = 50020

SLIDER_SAMPLING_HZ  = 5          # how often per second to log continuous slider

# ─────────────────────────────────────────────
# PUPIL CAPTURE HELPERS
# ─────────────────────────────────────────────
    
def connect_to_pupil_capture(ip, port):
    ctx = zmq.Context()
    # REQ socket for commands
    remote = ctx.socket(zmq.REQ)
    remote.setsockopt(zmq.RCVTIMEO, 10000)
    remote.setsockopt(zmq.SNDTIMEO, 10000)
    remote.connect(f"tcp://{ip}:{port}")
    # get PUB port
    remote.send_string("PUB_PORT")
    pub_port = remote.recv_string()
    # PUB socket for annotations
    pub = ctx.socket(zmq.PUB) 
    pub.connect(f"tcp://{ip}:{pub_port}")
    # sync clocks
    remote.send_string("T " + str(core.monotonicClock.getTime()))
    remote.recv_string()
    return ctx, remote, pub, pub_port

def send_annotation(pub_sock, label):
    annotation = {
        "topic": "annotation",
        "label": label,
        "timestamp": core.monotonicClock.getTime(),
        "duration": CHORD_DURATION,
    }
    payload = msgpack.dumps(annotation, use_bin_type=True)
    pub_sock.send_string(annotation["topic"], flags=zmq.SNDMORE)
    pub_sock.send(payload)

def start_pupil_recording(remote, session_name):
    remote.send_string(f"R {session_name}")
    _ = remote.recv_string()

def stop_pupil_recording(remote):
    remote.send_string("r")
    _ = remote.recv_string()

# ─────────────────────────────────────────────
# PARTICIPANT INFO DIALOG
# ─────────────────────────────────────────────

def get_participant_info():
    dlg = gui.Dlg(title="Chord Pleasantness Study")
    dlg.addField("Participant ID:")
    dlg.addField("Session:")
    info = dlg.show()
    if not dlg.OK:
        core.quit()
    return {"participant_id": info[0], "session": "1"}

# ─────────────────────────────────────────────
# LOAD STIMULI
# ─────────────────────────────────────────────

def load_stimuli(csv_path):
    stimuli = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stimuli.append(row)
    random.shuffle(stimuli)
    return stimuli

# ─────────────────────────────────────────────
# OVERALL RATING SCREEN
# ─────────────────────────────────────────────

def get_overall_rating(win, prompt_text, slider):
    """
    Show a 1-6 rating slider. Confirm button is greyed out until
    participant makes a selection, matching the Qualtrics behaviour.
    """
    prompt = visual.TextStim(
        win, text=prompt_text,
        pos=(0, 0.4), height=0.055, color="white",
        wrapWidth=1.6, alignText="center"
    )
    # Active confirm button (blue, matches Qualtrics arrow style)
    confirm_active = visual.Rect(
        win, width=0.22, height=0.09, pos=(0.75, -0.85),
        fillColor=[0.18, 0.45, 0.78], lineColor="white"
    )
    # Inactive confirm button (grey, before selection)
    confirm_inactive = visual.Rect(
        win, width=0.22, height=0.09, pos=(0.75, -0.85),
        fillColor=[0.5, 0.5, 0.5], lineColor=[0.5, 0.5, 0.5]
    )
    confirm_arrow = visual.TextStim(
        win, text="Submit", pos=(0.75, -0.85),
        height=0.05, color="white"
    )

    slider.reset()
    mouse = event.Mouse(win=win)

    while True:
        rating     = slider.getRating()
        has_rating = rating is not None

        prompt.draw()
        slider.draw()
        if has_rating:
            confirm_active.draw()
        else:
            confirm_inactive.draw()
        confirm_arrow.draw()
        win.flip()

        if has_rating and mouse.isPressedIn(confirm_active):
            core.wait(0.2)
            return rating

        if event.getKeys(["escape"]):
            core.quit()

# ─────────────────────────────────────────────
# MAIN EXPERIMENT
# ─────────────────────────────────────────────

def run_experiment():

    # ── participant info ──
    p_info  = get_participant_info()
    pid     = p_info["participant_id"]
    session = p_info["session"]

    # ── output CSV ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"sub-{pid}_ses-{session}_{timestamp}.csv")

    fieldnames = [
        "participant_id", "session", "trial_num", "trial_id",
        "stimulus_file",
        "sample_time",
        "chord_num_at_sample",
        "pleasantness_continuous",
        "overall_pleasantness",
        "overall_arousal",
    ]
    csvfile = open(output_file, "w", newline="")
    writer  = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # ── connect to Pupil Capture ──
    print("Connecting to Pupil Capture...")
    try:
        zmq_ctx, zmq_remote, zmq_pub, zmq_pub_port = connect_to_pupil_capture(PUPIL_CAPTURE_IP, PUPIL_CAPTURE_PORT)
        pupil_connected   = True
        print("Connected to Pupil Capture.")
        #start_pupil_recording(zmq_remote, f"sub-{pid}_ses-{session}")#test remove
    except Exception as e:
        print(f"WARNING: Could not connect to Pupil Capture: {e}")
        print("Continuing without pupillometry.")
        pupil_connected = False

    # ── window (uses Monitor Center profile for resolution) ──
    mon = monitors.Monitor(MONITOR_NAME)
    win = visual.Window(
        fullscr=False, # XXX for debugging. Switch back for experiment
        monitor=mon,
        color="black",
        units="norm"
    )
    win.mouseVisible = True

    # ── continuous pleasantness slider ──
    # Matches Qualtrics version: -100 to 100, starts at 0, fully continuous
    continuous_slider = visual.Slider(
        win,
        ticks=(-100, 0, 100),
        labels=["Very Unpleasant\n-100", "Neutral\n0", "Very Pleasant\n100"],
        startValue=0,
        pos=(0, -0.45),
        size=(1.5, 0.06),
        style="slider",
        color="white",
        fillColor=[0.4, 0.65, 0.9],
        borderColor="white",
        labelColor=[0.6, 0.6, 0.6],
        font="Arial",
        labelHeight=0.04,
        granularity=0,
        markerColor="lightblue",
        styleTweaks=["triangleMarker"]
    )
    continuous_slider.marker.size=(0.1, 0.1)
    
    rating_label = visual.TextStim(
        win, text="Rating",
        pos=(-0.75, -0.33), height=0.04,
        color=[0.6, 0.6, 0.6], anchorHoriz="left"
    )

    listen_instruction = visual.TextStim(
        win,
        text=(
            "After the 4-click countdown, move the slider to indicate how pleasant or\n"
            "unpleasant you find the sounds as you listen to the recording in real time.\n\n"
            "Evaluate \"pleasantness\" in terms of aesthetics rather than emotions."
        ),
        pos=(0, 0.55), height=0.05,
        color="white", wrapWidth=1.7, alignText="center"
    )

    locked_msg = visual.TextStim(
        win,
        text="You will be able to continue once the track has finished playing.",
        pos=(0, -0.75), height=0.04,
        color=[0.6, 0.6, 0.6]
    )

    # ── overall rating slider (1-6) ──
    overall_slider = visual.Slider(
        win,
        ticks=(1, 2, 3, 4, 5, 6),
        labels=["1", "2", "3", "4", "5", "6"],
        startValue=None,
        pos=(0, 0),
        size=(1.2, 0.07),
        style="rating",
        color="white",
        fillColor=[0.4, 0.65, 0.9],
        borderColor="white",
        labelColor="white",
        font="Arial",
        labelHeight=0.05,
        granularity=1
    )

    # ── instructions ──
    instructions = visual.TextStim(
        win,
        text=(
            "Welcome!\n\n"
            "You will listen to a series of chord sequences. As each chord plays, " 
            "use the slider to continuously rate how pleasant or unpleasant it sounds.\n\n"
            "Please evaluate \"pleasantness\" in terms of aesthetics "
            "rather than emotions. "
            "After each sequence you will give two overall ratings for the chord sequence "
            "as a whole: one for pleasantness, and one for perceived arousal.\n\n"
            "Please adjust your headphone volume to a "
            "comfortable level now.\n\n"
            "Press SPACE to begin."
        ),
        pos=(0, 0), height=0.055,
        color="white", wrapWidth=1.6, alignText="center"
    )
    instructions.draw()
    win.flip()
    event.waitKeys(keyList=["space"])



    # ─────────────────────────────────────────
    # TRIAL LOOP
    # ─────────────────────────────────────────
    stimuli = load_stimuli(STIMULI_CSV)
    for trial_num, stim in enumerate(stimuli):

        audio_path = os.path.join(STIMULI_DIR, stim["audio_file"])
        trial_id = str(trial_num + 1)

        total_audio_duration = COUNTDOWN_DURATION + N_CHORDS_PER_TRIAL * CHORD_DURATION
        chord_onset_times    = [
            COUNTDOWN_DURATION + c * CHORD_DURATION
            for c in range(N_CHORDS_PER_TRIAL)
        ]

        audio = sound.Sound(audio_path)
        if pupil_connected:
            zmq_pub.close()
            zmq_pub = zmq_ctx.socket(zmq.PUB)
            zmq_pub.connect(f"tcp://{PUPIL_CAPTURE_IP}:{zmq_pub_port}")
            sleep(1.0)
            start_pupil_recording(zmq_remote, f"sub-{pid}_trial-{trial_num + 1}")
            sleep(0.25)
            send_annotation(zmq_pub, f"trial_{trial_num + 1}_start")
            sleep(0.25)
        continuous_slider.reset()
#        continuous_slider.setRating(0)

        audio.play()
        trial_clock    = core.Clock()
        next_chord_idx = 0
        continuous_rows = []



        continuous_slider.setAutoDraw(True)
        # ── listening loop — advance LOCKED until audio ends ──
        while True:
            t = trial_clock.getTime()
            if t >= total_audio_duration:
                break

            # Pupil Capture annotation at each chord onset
            if next_chord_idx < N_CHORDS_PER_TRIAL:
                if t >= chord_onset_times[next_chord_idx]:
                    chord_num = next_chord_idx + 1
                    label = f"trial_{trial_id}_chord_{chord_num}"
                    if pupil_connected:
                        try:
                            send_annotation(zmq_pub, label)
                            print(f"Annotation sent: {label} at t={round(t,4)}")
                        except Exception as e:
                            print(f"Annotation error: {e}")
                    next_chord_idx += 1



            listen_instruction.draw()
            rating_label.draw()
            locked_msg.draw()
            current_pos = continuous_slider.getRating()
            # for debugging:
            print(f"t={round(t,2)} rating={current_pos}")
            if current_pos is not None and t >= COUNTDOWN_DURATION:
                # continuous_rows collects tuple of (value, time)
                # [-1][1] gets last row, last item
                if not continuous_rows or (t - continuous_rows[-1][1]) >= 1.0/SLIDER_SAMPLING_HZ:
                    continuous_rows.append((current_pos, t))
            win.flip()

            if event.getKeys(["escape"]):
                audio.stop()
                csvfile.close()
                if pupil_connected:
                    stop_pupil_recording(zmq_remote)
                win.close()
                core.quit()

        audio.stop()
        if pupil_connected:
            stop_pupil_recording(zmq_remote)
        continuous_slider.setAutoDraw(False)
        csvfile.flush()
        win.flip()
        core.wait(0.5)


        # ── overall pleasantness ──
        overall_pleasantness = get_overall_rating(
            win,
            "Rate how pleasant or unpleasant the whole sequence sounded to you overall.\n\n"
            "Evaluate \"pleasantness\" in terms of aesthetics rather than emotions.",
            overall_slider
        )

        # ── overall arousal (NEW) ──
        overall_arousal = get_overall_rating(
            win,
            "How arousing did you find that sequence overall?\n\n"
            "(1 = Not at all arousing,  6 = Very arousing)",
            overall_slider
        )

# ── write to CSV ──
        for (rating_val, t) in continuous_rows:
            chord_at_sample = None
            if t >= COUNTDOWN_DURATION:
                idx = int((t - COUNTDOWN_DURATION) / CHORD_DURATION)
                chord_at_sample = min(idx + 1, N_CHORDS_PER_TRIAL)
            writer.writerow({
                "participant_id":          pid,
                "session":                 session,
                "trial_num":               trial_num + 1,
                "trial_id":                trial_id,
                "stimulus_file":           stim["audio_file"],
                "sample_time":             round(t, 4),
                "chord_num_at_sample":     chord_at_sample,
                "pleasantness_continuous": rating_val,
                "overall_pleasantness":    overall_pleasantness,
                "overall_arousal":         overall_arousal,
            })

        # Brief inter-trial blank, first write to file after every trial
        csvfile.flush()  # write to file
        win.flip()
        core.wait(0.5)

    # ─────────────────────────────────────────
    # END OF EXPERIMENT
    # ─────────────────────────────────────────
    end_screen = visual.TextStim(
        win,
        text=(
            "Thank you for completing the listening task!\n\n"
            "You will now answer a few brief questionnaires.\n\n"
            "Press SPACE to continue."
        ),
        pos=(0, 0), height=0.06,
        color="white", wrapWidth=1.6, alignText="center"
    )
    end_screen.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    # Demographics placeholder
    for q in ["What is your age?", "What is your gender?"]:
        dlg = gui.Dlg(title="Questionnaire")
        dlg.addField(q)
        dlg.show()

    farewell = visual.TextStim(
        win,
        text="The study is now complete.\nThank you for your participation!",
        pos=(0, 0), height=0.07, color="white"
    )
    farewell.draw()
    win.flip()
    core.wait(3)

    csvfile.close()
    if pupil_connected:
        zmq_ctx.term()
    win.close()
    core.quit()


if __name__ == "__main__":
    run_experiment()
