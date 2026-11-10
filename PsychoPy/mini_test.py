"""
Mini test: slider vs. fixation-cross (pupil noise comparison)
-------------------------------------------------------------
Flow:
  Audio check -> Instructions -> Pupil baseline -> 4 trials in RANDOM order

The 4 trials = 2 stimuli x 2 conditions:
  * "slider"   : Ling's original trial (baseline "Please wait..." screen 0.5 s,
                 audio + continuous slider, overall pleasantness/arousal/familiarity)
  * "fixation" : -> cross fixation


Needs chord_pleasantness_experiment.py (Ling's file) and her helper modules
(config, screens, ui, pupil, data_logging, survey_content) in the same folder.
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import csv
import glob
import os
import platform
import random
from datetime import datetime

# Importing Ling's file also sets the audio prefs (before psychopy.sound loads)
import chord_pleasantness_experiment as ling
import config
import psychopy
import screens
import survey_content as content
import ui
from data_logging import SessionLogs
from psychopy import core, event, sound, visual
from pupil import PupilCapture

# ─────────────────────────────────────────────
# MINI-TEST SETTINGS
# ─────────────────────────────────────────────
N_STIMULI = 2                 # each stimulus is played once per condition -> 2 x 2 = 4 trials
MINI_STIMULI = None
CONDITIONS = ("slider", "fixation")

# Fixation cross (units = 'height'), same as w.fixation.py
FIX_ARM_LENGTH = 0.05
FIX_THICKNESS = 0.006
FIX_COLOR = "white"


# ─────────────────────────────────────────────
# FIXATION CROSS
# ─────────────────────────────────────────────
class Fixation:
    def __init__(self, win):
        self.h = visual.Rect(win, units="height", width=FIX_ARM_LENGTH, height=FIX_THICKNESS,
                             pos=(0, 0), fillColor=FIX_COLOR, lineColor=FIX_COLOR)
        self.v = visual.Rect(win, units="height", width=FIX_THICKNESS, height=FIX_ARM_LENGTH,
                             pos=(0, 0), fillColor=FIX_COLOR, lineColor=FIX_COLOR)

    def draw(self):
        self.h.draw()
        self.v.draw()


def run_trial_baseline_cross(win, pupil, fixation, trial_num):
    """Same as Ling's run_trial_baseline (TRIAL_BASELINE_DURATION, annotation on the first frame), but the screen shows a fixation cross instead of text."""
    annotation_times = []
    fixation.draw()
    win.callOnFlip(lambda: annotation_times.append(
        pupil.annotate(f"trial_{trial_num}_baseline", duration=config.TRIAL_BASELINE_DURATION)))
    win.flip()
    clock = core.Clock()
    while clock.getTime() < config.TRIAL_BASELINE_DURATION:
        fixation.draw()
        win.flip()
        ui.poll_control_keys()          # lets the quit key work during baseline
    return annotation_times[0] if annotation_times else None


def play_with_fixation(win, fixation, pupil, audio, trial_num, n_chords):
 
    chord_onset_times = [config.COUNTDOWN_DURATION + c * config.CHORD_DURATION
                         for c in range(n_chords)]
    next_chord_idx = 0
    skipped = False

    trial_clock = core.Clock()
    win.callOnFlip(audio.play)
    win.callOnFlip(trial_clock.reset)
    fixation.draw()
    win.flip()
    audio_onset_time = core.monotonicClock.getTime() - trial_clock.getTime()

    duration = audio.getDuration()
    while True:
        t = trial_clock.getTime()
        if t >= duration + 0.1:
            break
        if next_chord_idx < n_chords and t >= chord_onset_times[next_chord_idx]:
            next_chord_idx += 1
            pupil.annotate(f"trial_{trial_num}_chord_{next_chord_idx}")
        fixation.draw()
        win.flip()
        if ui.poll_control_keys():
            skipped = True
            break
    return audio_onset_time, skipped


# ─────────────────────────────────────────────
# TRIAL
# ─────────────────────────────────────────────
def show_cue(win, text):
    stim = visual.TextStim(win, text=text + "\n\nPress SPACE to start.", pos=(0, 0),
                           height=0.055, color="white", wrapWidth=1.6, alignText="center")
    win.mouseVisible = True
    stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        raise ui.ExperimentAborted()


def run_mini_trial(win, listening_screen, fixation, pupil, logs, cond_writer, cond_file,
                   trial_num, audio_path, condition):
    stimulus_file = os.path.basename(audio_path)
    audio = sound.Sound(audio_path)
    audio_duration = audio.getDuration()
    n_chords = max(0, int((audio_duration - config.COUNTDOWN_DURATION) // config.CHORD_DURATION))
    print(f"Trial {trial_num} [{condition}]: {stimulus_file}  "
          f"duration={audio_duration:.2f}s  chords={n_chords}")

    pupil.start_recording(f"sub-{logs.participant_id}_trial-{trial_num}")
    trial_start_annotation_time = pupil.annotate(f"trial_{trial_num}_start")
    dropped_frames_before = win.nDroppedFrames
    samples = []
    try:
        if condition == "slider":
            baseline_time = ling.run_trial_baseline(win, pupil, trial_num)
            audio_onset_time, skipped = ling.play_with_continuous_rating(
                win, listening_screen, pupil, audio, trial_num, n_chords, samples)
        else:
            baseline_time = run_trial_baseline_cross(win, pupil, fixation, trial_num)
            audio_onset_time, skipped = play_with_fixation(
                win, fixation, pupil, audio, trial_num, n_chords)
    finally:
        audio.stop()
        pupil.stop_recording()
        if samples:
            logs.continuous.write_rows({
                "block": condition, "trial_num": trial_num, "stimulus_file": stimulus_file,
                "sample_num": i, "sample_time": round(t, 4),
                "chord_num_at_sample": ling.chord_at(t, n_chords), "pleasantness_continuous": r,
            } for i, (t, r) in enumerate(samples, start=1))
    n_dropped_frames = win.nDroppedFrames - dropped_frames_before
    win.flip()
    core.wait(0.5)

    overall_pleasantness, pleasantness_rt = screens.run_overall_rating(win, content.OVERALL_PLEASANTNESS_PROMPT)
    overall_arousal, arousal_rt = screens.run_overall_rating(win, content.OVERALL_AROUSAL_PROMPT)
    recognized_song, recognized_song_name = screens.run_familiarity(win)

    logs.trials.write_row({
        "block": condition, "trial_num": trial_num, "stimulus_file": stimulus_file,
        "audio_duration": round(audio_duration, 3), "n_chords": n_chords,
        "audio_onset_time": round(audio_onset_time, 4),
        "trial_start_annotation_time": trial_start_annotation_time,
        "trial_baseline_annotation_time": baseline_time,
        "slider_touched": any(r is not None for _, r in samples),
        "n_continuous_samples": len(samples), "n_dropped_frames": n_dropped_frames,
        "overall_pleasantness": overall_pleasantness, "overall_pleasantness_rt": round(pleasantness_rt, 3),
        "overall_arousal": overall_arousal, "overall_arousal_rt": round(arousal_rt, 3),
        "recognized_song": recognized_song, "recognized_song_name": recognized_song_name,
        "skipped": skipped, "completed_wallclock": datetime.now().isoformat(timespec="seconds"),
    })
    cond_writer.writerow({
        "participant_id": logs.participant_id, "trial_num": trial_num,
        "condition": condition, "stimulus_file": stimulus_file,
        "audio_onset_time": round(audio_onset_time, 4),
        "trial_start_annotation_time": trial_start_annotation_time,
        "trial_baseline_annotation_time": baseline_time,
    })
    cond_file.flush()
    win.flip()
    core.wait(config.INTER_TRIAL_INTERVAL)


# ─────────────────────────────────────────────
# PLAN
# ─────────────────────────────────────────────
def build_mini_plan(rng):
    """Returns a randomly ordered list of (audio_path, condition) with 4 entries.
    The same stimulus is never played twice in a row."""
    for name in ("VOLUME_CHECK_STIMULUS",):
        path = getattr(config, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{name} not found: '{os.path.abspath(path)}'")

    if MINI_STIMULI:
        stims = list(MINI_STIMULI)
    else:
        paths = sorted(glob.glob(os.path.join(config.STIMULI_DIR, "*.wav")))
        if len(paths) < N_STIMULI:
            raise FileNotFoundError(f"Need >= {N_STIMULI} .wav files in '{os.path.abspath(config.STIMULI_DIR)}'")
        by_seq = {}
        for p in paths:
            by_seq.setdefault(ling.sequence_id(p), []).append(p)
        seqs = rng.sample(sorted(by_seq), N_STIMULI)          # different sequences
        stims = [rng.choice(by_seq[s]) for s in seqs]

    trials = [(s, c) for s in stims for c in CONDITIONS]
    for _ in range(10000):
        rng.shuffle(trials)
        if all(ling.sequence_id(a[0]) != ling.sequence_id(b[0]) for a, b in zip(trials, trials[1:])):
            return trials
    raise RuntimeError("Could not find an order without back-to-back repeats of a stimulus.")


# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
MINI_INSTRUCTIONS = (
    "You will hear 4 short chord sequences.\n\n"
    "In some trials a slider will appear: move it to continuously rate how pleasant "
    "the chords sound.\n\n"
    "In other trials there is only a cross in the center of the screen: keep your "
    "eyes on the cross and just listen.\n\n"
    "After each sequence you will answer a few short questions. "
    "Please evaluate \"pleasantness\" in terms of aesthetics rather than emotions."
)
CUE_TEXT = {
    "slider": "In this trial, use the slider to rate the chords as you listen.",
    "fixation": "In this trial, keep your eyes on the cross in the center and just listen.\nThere is no slider.",
}


def run_mini_session(win, pupil, logs, plan, cond_writer, cond_file):
    listening_screen = screens.ListeningScreen(win, content.LISTENING_SCREEN_TEXT)
    fixation = Fixation(win)

    def trial_step(trial_num, path, condition):
        def step():
            show_cue(win, CUE_TEXT[condition])
            run_mini_trial(win, listening_screen, fixation, pupil, logs, cond_writer, cond_file,
                           trial_num, path, condition)
        return step

    steps = [
        lambda: screens.run_audio_check(win, sound.Sound(config.VOLUME_CHECK_STIMULUS),
                                        content.AUDIO_CHECK_TEXT),
        lambda: screens.show_text_page(win, "Instructions", MINI_INSTRUCTIONS, next_label="Next"),
        lambda: ling.run_pupil_baseline(win, pupil, logs),
        *[trial_step(i, path, cond) for i, (path, cond) in enumerate(plan, start=1)],
    ]

    progress = ui.session_progress
    progress.total = len(steps)
    for step in steps:
        step()
        progress.step()

    farewell = visual.TextStim(win, text="The mini test is complete.\nThank you!",
                               pos=(0, 0), height=0.07, color="white")
    farewell.draw()
    win.flip()
    core.wait(3)
    return "completed"


def main():
    participant_id, session = ling.get_participant_info()
    random_seed = random.randrange(2 ** 32)
    rng = random.Random(random_seed)
    plan = build_mini_plan(rng)
    started = datetime.now()
    stem = f"sub-{participant_id}_ses-{session}_{started:%Y%m%d_%H%M%S}"

    logs = SessionLogs(config.OUTPUT_DIR, stem, participant_id, session)
    pupil = PupilCapture(config.USE_PUPIL, config.PUPIL_CAPTURE_IP, config.PUPIL_CAPTURE_PORT)
    win = ling.open_window()

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    cond_file = open(os.path.join(config.OUTPUT_DIR, f"{stem}_mini_conditions.csv"), "w", newline="")
    cond_writer = csv.DictWriter(cond_file, fieldnames=[
        "participant_id", "trial_num", "condition", "stimulus_file", "audio_onset_time",
        "trial_start_annotation_time", "trial_baseline_annotation_time"])
    cond_writer.writeheader()

    logs.update_session_info(
        participant_id=participant_id, session=session, status="running",
        start_wallclock=started.isoformat(timespec="seconds"),
        machine=config.MACHINE, pupil_connected=pupil.connected,
        psychopy_version=psychopy.__version__, python_version=platform.python_version(),
        platform=platform.platform(), window_size=[int(px) for px in win.size],
        frame_rate=win.getActualFrameRate(), random_seed=random_seed,
        mini_test_order=[{"trial_num": i, "condition": c, "stimulus_file": os.path.basename(p)}
                         for i, (p, c) in enumerate(plan, start=1)],
        config=ling.config_snapshot(),
    )

    status = "error"
    try:
        status = run_mini_session(win, pupil, logs, plan, cond_writer, cond_file)
    except ui.ExperimentAborted:
        status = "aborted"
        print("Session aborted with the quit key; recorded data is saved.")
    finally:
        cond_file.close()
        pupil.close()
        logs.update_session_info(status=status, end_wallclock=datetime.now().isoformat(timespec="seconds"))
        logs.close()
        win.close()
    core.quit()


if __name__ == "__main__":
    main()
