"""
Output files for one session (all in OUTPUT_DIR, sharing one prefix):

  <prefix>_continuous.csv      one row per continuous-slider sample
  <prefix>_trials.csv          one row per trial (overall ratings, familiarity, timing)
  <prefix>_questionnaires.csv  one row per answered item (consent, demographics, BMRQ, Gold-MSI)
  <prefix>_session.json        settings, stimulus order, versions, completion status

All times are seconds on core.monotonicClock (the clock Pupil Capture is synced to)
unless the column name ends in "_wallclock". Missing values are written as NA.
Every row is flushed and fsynced immediately, so an aborted session keeps all
completed rows.
"""
import csv
import json
import os
from collections import namedtuple

NA = "NA"

# One answered questionnaire item. response = numeric code (1-based option index,
# or the typed value); response_label = the option text shown.
ItemResponse = namedtuple("ItemResponse", ["item_id", "item_text", "response", "response_label", "page_rt"])

CONTINUOUS_FIELDS = [
    "participant_id", "session", "block", "trial_num", "stimulus_file",
    "sample_num", "sample_time", "chord_num_at_sample", "pleasantness_continuous",
]

TRIAL_FIELDS = [
    "participant_id", "session", "block", "trial_num", "stimulus_file",
    "audio_duration", "n_chords", "audio_onset_time", "trial_start_annotation_time",
    "trial_baseline_annotation_time",
    "slider_touched", "n_continuous_samples", "n_dropped_frames",
    "overall_pleasantness", "overall_pleasantness_rt",
    "overall_arousal", "overall_arousal_rt",
    "recognized_song", "recognized_song_name",
    "skipped", "completed_wallclock",
]

QUESTIONNAIRE_FIELDS = [
    "participant_id", "session", "questionnaire", "item_id", "item_text",
    "response", "response_label", "page_rt",
]


class CsvLog:
    """CSV writer with a fixed schema; constant columns (e.g. participant_id) are filled in."""

    def __init__(self, path, fieldnames, constant_fields):
        self.path = path
        self.constant_fields = constant_fields
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames, restval=NA)
        self._writer.writeheader()
        self._sync()

    def write_rows(self, rows):
        for row in rows:
            self._writer.writerow({**self.constant_fields,
                                   **{k: NA if v is None else v for k, v in row.items()}})
        self._sync()

    def write_row(self, row):
        self.write_rows([row])

    def _sync(self):
        self._file.flush()
        os.fsync(self._file.fileno())

    def close(self):
        if not self._file.closed:
            self._file.close()


class SessionLogs:

    def __init__(self, output_dir, file_prefix, participant_id, session):
        os.makedirs(output_dir, exist_ok=True)
        self.participant_id, self.session = participant_id, session
        base = os.path.join(output_dir, file_prefix)
        ids = {"participant_id": participant_id, "session": session}
        self.continuous = CsvLog(base + "_continuous.csv", CONTINUOUS_FIELDS, ids)
        self.trials = CsvLog(base + "_trials.csv", TRIAL_FIELDS, ids)
        self.questionnaires = CsvLog(base + "_questionnaires.csv", QUESTIONNAIRE_FIELDS, ids)
        self.session_info_path = base + "_session.json"
        self.session_info = {}

    def update_session_info(self, **fields):
        """Rewrites the JSON atomically, so it is never left half-written."""
        self.session_info.update(fields)
        tmp_path = self.session_info_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.session_info, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.session_info_path)

    def write_responses(self, questionnaire, responses):
        self.questionnaires.write_rows(
            {"questionnaire": questionnaire, **response._asdict()} for response in responses)

    def close(self):
        for log in (self.continuous, self.trials, self.questionnaires):
            log.close()
