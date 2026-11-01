"""
Chord Pleasantness Experiment
------------------------------
PsychoPy experiment for in-person study of chord pleasantness ratings
with Pupil Labs (Pupil Capture) pupillometry integration.

Session flow:
  Consent -> Audio adjustment -> Instructions -> Pupil baseline -> Practice trial
  -> Block 1 (first half of STIMULI_DIR) -> Demographics -> BMRQ
  -> Block 2 (second half) -> Gold-MSI

Structure per trial:
  0. Pupil baseline: "Please wait..." screen for TRIAL_BASELINE_DURATION (0.5 s)
  1. Audio file plays (countdown + chords at 2.4s each; length read from the file)
  2. Continuous pleasantness slider active throughout (advance LOCKED until audio ends)
  3. ZMQ annotations sent to Pupil Capture at each chord onset (after countdown)
  4. After audio: overall pleasantness rating (1-6)
  5. After that: overall arousal rating (1-6)
  6. Repeat for every .wav in STIMULI_DIR (random order)

Requirements:
  pip install pyzmq

Settings live in config.py (set MACHINE = "booth" or "laptop"); participant-facing
text in survey_content.py; output files are described in data_logging.py.
When USE_PUPIL=TRUE, Pupil Capture must be running before the experiment starts.
Set PUPIL_CAPTURE_IP if Pupil Capture is on a different machine.
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import config
from psychopy import prefs
# audio prefs must be set before psychopy.sound is imported
prefs.hardware["audioLib"] = config.AUDIO_LIB
if config.AUDIO_DEVICE:
    prefs.hardware["audioDevice"] = config.AUDIO_DEVICE

import glob
import itertools
import platform
import random
from datetime import datetime

import psychopy
from psychopy import visual, core, sound, gui, monitors

import screens
import survey_content as content
import ui
from data_logging import SessionLogs
from pupil import PupilCapture

# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────

def get_participant_info():
    """Experimenter dialog; re-asks until the participant ID is usable in a file name."""
    error = ""
    while True:
        dlg = gui.Dlg(title="Chord Pleasantness Study")
        if error:
            dlg.addText(error)
        dlg.addField("Participant ID:")
        dlg.addField("Session:", "1")
        info = dlg.show()
        if not dlg.OK:
            core.quit()
        pid, session = str(info[0]).strip(), str(info[1]).strip() or "1"
        if pid and all(c.isalnum() or c in "-_" for c in pid + session):
            return pid, session
        error = "Use letters, digits, '-' or '_' only."


def sequence_id(path):
    """'1_24' for 1_24_Bb_O.wav, 1_24_Bb_S.wav, 1_24_Bb_O_inv.wav, ... (every version of a sequence)."""
    return "_".join(os.path.basename(path).split("_")[:2])


def load_stimuli(stim_dir, rng, max_tries=10000):
    """
    All .wav paths in stim_dir, shuffled with the session's seeded RNG so that no two
    consecutive files share a sequence_id. Reshuffling until that holds keeps every valid
    order equally likely; about 1 in 5 shuffles of the 38 study stimuli passes.
    """
    paths = sorted(glob.glob(os.path.join(stim_dir, "*.wav")))
    if not paths:
        raise FileNotFoundError(f"No .wav files found in '{os.path.abspath(stim_dir)}'")
    for _ in range(max_tries):
        rng.shuffle(paths)
        if all(sequence_id(a) != sequence_id(b) for a, b in zip(paths, paths[1:])):
            return paths
    raise RuntimeError(f"No order of '{stim_dir}' avoids back-to-back versions of a sequence; "
                       "are the files named like 1_24_Bb_O.wav?")


def shuffled_range(n, rng):
    order = list(range(n))
    rng.shuffle(order)
    return order


def build_stimulus_plan(rng):
    """Block name -> ordered stimulus paths. Fails before the session starts if files are missing."""
    for name in ("PRACTICE_STIMULUS", "VOLUME_CHECK_STIMULUS"):
        path = getattr(config, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{name} not found: '{os.path.abspath(path)}'")
    main = load_stimuli(config.STIMULI_DIR, rng)
    half = len(main) // 2
    return {
        "practice":  [config.PRACTICE_STIMULUS],
        "main_1":    main[:half],
        "main_2":    main[half:],
    }


def open_window():
    win = visual.Window(
        fullscr=config.FULLSCREEN, 
        monitor=monitors.Monitor(config.MONITOR_NAME),
        color="black", 
        units="norm"
    )
    win.mouseVisible = True
    win.recordFrameIntervals = True   # enables win.nDroppedFrames for the per-trial timing check
    return win


def config_snapshot():
    return {name: getattr(config, name) for name in dir(config) if name.isupper()}

# ─────────────────────────────────────────────
# TRIAL
# ─────────────────────────────────────────────

def chord_at(t, n_chords):
    """1-based chord playing at trial time t, or None during the countdown."""
    if t < config.COUNTDOWN_DURATION or n_chords == 0:
        return None
    idx = int((t - config.COUNTDOWN_DURATION) / config.CHORD_DURATION)
    return max(1, min(idx + 1, n_chords))


def run_trial_baseline(win, pupil, trial_num):
    """Baseline screen for TRIAL_BASELINE_DURATION right before audio onset.
    Returns the time of the baseline annotation, sent on the screen's first frame."""
    annotation_times = []
    screens.show_baseline_screen(
        win, config.TRIAL_BASELINE_DURATION, content.TRIAL_BASELINE_MESSAGE,
        on_first_flip=lambda: annotation_times.append(pupil.annotate(
            f"trial_{trial_num}_baseline", duration=config.TRIAL_BASELINE_DURATION)))
    return annotation_times[0] if annotation_times else None


def play_with_continuous_rating(win, listening_screen, pupil, audio, trial_num, n_chords, samples):
    """
    Plays the stimulus while sampling the continuous slider. Appends (trial_time,
    rating or None) to `samples` in place, so the caller keeps them even if the
    quit key interrupts playback. Returns (audio_onset_time, skipped).
    """
    chord_onset_times = [config.COUNTDOWN_DURATION + c * config.CHORD_DURATION
                         for c in range(n_chords)]
    sample_period = 1.0 / config.SLIDER_SAMPLING_HZ
    next_sample_time = config.COUNTDOWN_DURATION
    next_chord_idx = 0
    skipped = False
    listening_screen.reset()

    # audio onset and clock zero are both locked to the first screen flip,
    # so chord_onset_times line up with what the participant actually hears
    trial_clock = core.Clock()
    win.callOnFlip(audio.play)
    win.callOnFlip(trial_clock.reset)
    win.flip()
    audio_onset_time = core.monotonicClock.getTime() - trial_clock.getTime()

    duration = audio.getDuration()
    while True:
        t = trial_clock.getTime()
        if t >= duration + 0.1:
            break

        # Pupil Capture annotation at each chord onset
        if next_chord_idx < n_chords and t >= chord_onset_times[next_chord_idx]:
            next_chord_idx += 1
            pupil.annotate(f"trial_{trial_num}_chord_{next_chord_idx}")

        rating = listening_screen.update_and_draw()
        # samples follow a fixed schedule so the rate does not drift with frame timing
        if t >= next_sample_time:
            samples.append((t, rating))
            while next_sample_time <= t:
                next_sample_time += sample_period
        win.flip()

        if ui.poll_control_keys():
            skipped = True
            break
    return audio_onset_time, skipped


def run_trial(win, listening_screen, pupil, logs, block, trial_num, audio_path):
    stimulus_file = os.path.basename(audio_path)
    audio = sound.Sound(audio_path)
    audio_duration = audio.getDuration()
    n_chords = max(0, int((audio_duration - config.COUNTDOWN_DURATION) // config.CHORD_DURATION))
    print(f"Trial {trial_num} [{block}]: {stimulus_file}  "
          f"duration={audio_duration:.2f}s  chords={n_chords}")

    pupil.start_recording(f"sub-{logs.participant_id}_trial-{trial_num}")
    trial_start_annotation_time = pupil.annotate(f"trial_{trial_num}_start")
    dropped_frames_before = win.nDroppedFrames
    samples = []
    try:
        trial_baseline_annotation_time = run_trial_baseline(win, pupil, trial_num)
        audio_onset_time, skipped = play_with_continuous_rating(
            win, listening_screen, pupil, audio, trial_num, n_chords, samples)
    finally:
        audio.stop()
        pupil.stop_recording()
        # saved before the post-trial questions, and also when the quit key interrupts playback
        logs.continuous.write_rows({
            "block": block, "trial_num": trial_num, "stimulus_file": stimulus_file,
            "sample_num": sample_num, "sample_time": round(t, 4),
            "chord_num_at_sample": chord_at(t, n_chords), "pleasantness_continuous": rating,
        } for sample_num, (t, rating) in enumerate(samples, start=1))
    n_dropped_frames = win.nDroppedFrames - dropped_frames_before
    win.flip()
    core.wait(0.5)

    overall_pleasantness, pleasantness_rt = screens.run_overall_rating(win, content.OVERALL_PLEASANTNESS_PROMPT)
    overall_arousal, arousal_rt = screens.run_overall_rating(win, content.OVERALL_AROUSAL_PROMPT)
    recognized_song, recognized_song_name = screens.run_familiarity(win)

    logs.trials.write_row({
        "block": block, "trial_num": trial_num, "stimulus_file": stimulus_file,
        "audio_duration": round(audio_duration, 3), "n_chords": n_chords,
        "audio_onset_time": round(audio_onset_time, 4),
        "trial_start_annotation_time": trial_start_annotation_time,
        "trial_baseline_annotation_time": trial_baseline_annotation_time,
        "slider_touched": any(rating is not None for _, rating in samples),
        "n_continuous_samples": len(samples), "n_dropped_frames": n_dropped_frames,
        "overall_pleasantness": overall_pleasantness, "overall_pleasantness_rt": round(pleasantness_rt, 3),
        "overall_arousal": overall_arousal, "overall_arousal_rt": round(arousal_rt, 3),
        "recognized_song": recognized_song, "recognized_song_name": recognized_song_name,
        "skipped": skipped, "completed_wallclock": datetime.now().isoformat(timespec="seconds"),
    })
    win.flip()
    core.wait(config.INTER_TRIAL_INTERVAL)


def run_pupil_baseline(win, pupil, logs):
    pupil.start_recording(f"sub-{logs.participant_id}_baseline")
    start_time = pupil.annotate("baseline_start", duration=config.BASELINE_DURATION)
    try:
        screens.show_baseline_screen(win, config.BASELINE_DURATION, content.BASELINE_MESSAGE)
        end_time = pupil.annotate("baseline_end", duration=0)
    finally:
        pupil.stop_recording()
    logs.update_session_info(baseline_annotation_times={"start": start_time, "end": end_time})

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────

DECLINED = object()   # returned by the consent step to end the session early


def run_session(win, pupil, logs, plan, item_orders):
    """
    Runs the full flow; returns the session status for the session JSON. The flow is one
    list of steps (a screen, questionnaire or trial each), so the progress bar's total is
    simply len(steps) and stays right when steps are added or removed.
    """
    listening_screen = screens.ListeningScreen(win, content.LISTENING_SCREEN_TEXT)
    trial_nums = itertools.count(1)   # numbering continues across blocks; practice is trial 0

    def consent():
        consented, responses = screens.run_consent(win, content.CONSENT_TEXT, content.CONSENT_AGREEMENT)
        logs.write_responses("consent", responses)
        if not consented:
            screens.show_text_page(win, "Thank you", content.NO_CONSENT_TEXT, next_label="Exit")
            return DECLINED

    def page(title, body, next_label="Next"):
        return lambda: screens.show_text_page(win, title, body, next_label=next_label)

    def trial(block, trial_num, audio_path):
        return lambda: run_trial(win, listening_screen, pupil, logs, block, trial_num, audio_path)

    def block(name):
        return [trial(name, next(trial_nums), path) for path in plan[name]]

    def questionnaire(name, run):
        return lambda: logs.write_responses(name, run())

    # Likert values are raw (1-7); reverse-keyed items are scored during analysis
    steps = [
        consent,
        lambda: screens.run_audio_check(win, sound.Sound(config.VOLUME_CHECK_STIMULUS),
                                        content.AUDIO_CHECK_TEXT),
        page("Instructions", content.LISTENING_INSTRUCTIONS),
        lambda: run_pupil_baseline(win, pupil, logs),
        page("Practice", content.PRACTICE_INTRO, next_label="Start"),
        trial("practice", 0, config.PRACTICE_STIMULUS),

        page("Instructions", content.MAIN_TASK_INTRO, next_label="Start"),
        *block("main_1"),

        page(None, content.FIRST_HALF_DONE),
        questionnaire("demographics", lambda: screens.run_demographics(win, content.GENDER_OPTIONS)),
        questionnaire("bmrq", lambda: screens.run_matrix_questionnaire(
            win, "bmrq", None, content.MATRIX_INSTRUCTION,
            content.BMRQ_ITEMS, content.BMRQ_SCALE, order=item_orders["bmrq"])),

        page(None, content.SECOND_HALF_INTRO, next_label="Start"),
        *block("main_2"),

        page(None, content.FINAL_QUESTIONNAIRE_INTRO),
        questionnaire("gold_msi", lambda: screens.run_matrix_questionnaire(
            win, "gold_msi", None, content.MATRIX_INSTRUCTION,
            content.GOLD_MSI_ITEMS, content.GOLD_MSI_SCALE, order=item_orders["gold_msi"])),
        questionnaire("gold_msi", lambda: screens.run_choice_questions(
            win, "gold_msi", None, content.GOLD_MSI_TRAINING_QUESTIONS,
            first_item_num=len(content.GOLD_MSI_ITEMS) + 1, order=item_orders["gold_msi_training"])),
    ]

    progress = ui.session_progress
    progress.total = len(steps)
    for step in steps:
        if step() is DECLINED:
            return "no_consent"
        progress.step()

    farewell = visual.TextStim(win, text="The study is now complete.\nThank you for your participation!",
                               pos=(0, 0), height=0.07, color="white")
    farewell.draw()
    win.flip()
    core.wait(3)
    return "completed"


def main():
    participant_id, session = get_participant_info()
    random_seed = random.randrange(2 ** 32)
    rng = random.Random(random_seed)
    plan = build_stimulus_plan(rng)
    item_orders = {   # display order of questionnaire items (indices into survey_content lists)
        "bmrq":              shuffled_range(len(content.BMRQ_ITEMS), rng),
        "gold_msi":          shuffled_range(len(content.GOLD_MSI_ITEMS), rng),
        "gold_msi_training": shuffled_range(len(content.GOLD_MSI_TRAINING_QUESTIONS), rng),
    }
    started = datetime.now()

    logs = SessionLogs(config.OUTPUT_DIR, f"sub-{participant_id}_ses-{session}_{started:%Y%m%d_%H%M%S}",
                       participant_id, session)
    pupil = PupilCapture(config.USE_PUPIL, config.PUPIL_CAPTURE_IP, config.PUPIL_CAPTURE_PORT)
    win = open_window()
    logs.update_session_info(
        participant_id=participant_id, session=session, status="running",
        start_wallclock=started.isoformat(timespec="seconds"),
        machine=config.MACHINE, pupil_connected=pupil.connected,
        psychopy_version=psychopy.__version__, python_version=platform.python_version(),
        platform=platform.platform(), window_size=[int(px) for px in win.size],
        frame_rate=win.getActualFrameRate(), random_seed=random_seed,
        stimulus_order={block: [os.path.basename(p) for p in paths] for block, paths in plan.items()},
        questionnaire_item_order={name: [i + 1 for i in order] for name, order in item_orders.items()},
        config=config_snapshot(),
    )

    status = "error"   # kept if an unexpected exception escapes
    try:
        status = run_session(win, pupil, logs, plan, item_orders)
    except ui.ExperimentAborted:
        status = "aborted"
        print("Session aborted with the quit key; recorded data is saved.")
    finally:
        pupil.close()
        logs.update_session_info(status=status, end_wallclock=datetime.now().isoformat(timespec="seconds"))
        logs.close()
        win.close()
    core.quit()


if __name__ == "__main__":
    main()
