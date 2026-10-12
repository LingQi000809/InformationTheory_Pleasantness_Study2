#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Chord pleasantness and pupil-dilation mapping")
    parser.add_argument("--annotation", default="annotation.csv")
    parser.add_argument("--pupil", default="pupil_positions.csv")
    parser.add_argument("--ratings", default="sub-1_ses-1_20261007_162806.csv")
    parser.add_argument("--outdir", default="chord_mapping_output")
    parser.add_argument("--method", default="2d c++")
    parser.add_argument("--eye", choices=["both", "0", "1"], default="both")
    args = parser.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    annotation = pd.read_csv(args.annotation)
    pupil = pd.read_csv(args.pupil)
    ratings = pd.read_csv(args.ratings)

    annotation = annotation[annotation["label"].astype(str).str.contains(r"_chord_\d+$")].copy()
    annotation["trial_num"] = annotation["label"].str.extract(r"trial_(\d+)_")[0].astype(int)
    annotation["chord_num"] = annotation["label"].str.extract(r"_chord_(\d+)$")[0].astype(int)
    annotation["start_time"] = pd.to_numeric(annotation["timestamp"], errors="coerce")
    annotation["duration"] = pd.to_numeric(annotation.get("duration", 2.4), errors="coerce").fillna(2.4)
    annotation["end_time"] = annotation["start_time"] + annotation["duration"]
    annotation = annotation.dropna(subset=["start_time"]).sort_values(["trial_num", "chord_num"])

    pupil["pupil_timestamp"] = pd.to_numeric(pupil["pupil_timestamp"], errors="coerce")
    pupil["diameter"] = pd.to_numeric(pupil["diameter"], errors="coerce")
    pupil["eye_id"] = pd.to_numeric(pupil["eye_id"], errors="coerce")
    pupil = pupil[
        pupil["method"].astype(str).eq(args.method)
        & pupil["pupil_timestamp"].notna()
        & pupil["diameter"].notna()
    ].copy()
    if args.eye != "both":
        pupil = pupil[pupil["eye_id"] == int(args.eye)]

    print("Chord Pleasantness Experiment")
    print(f"Chord annotations: {len(annotation)}")
    print(f"Pupil timestamp range: {pupil['pupil_timestamp'].min():.3f}–{pupil['pupil_timestamp'].max():.3f} s")
    print(f"Annotation timestamp range: {annotation['start_time'].min():.3f}–{annotation['end_time'].max():.3f} s")

    sample_parts, vector_rows, summary_rows = [], [], []
    for chord in annotation.itertuples(index=False):
        window = pupil[
            (pupil["pupil_timestamp"] >= chord.start_time)
            & (pupil["pupil_timestamp"] < chord.end_time)
        ].sort_values("pupil_timestamp")

        for eye_id in sorted(pupil["eye_id"].dropna().unique()):
            eye_data = window[window["eye_id"] == eye_id]
            times = eye_data["pupil_timestamp"].astype(float).tolist()
            values = eye_data["diameter"].astype(float).tolist()

            vector_rows.append({
                "trial_num": chord.trial_num,
                "chord_num": chord.chord_num,
                "stimulus_file": chord.label,
                "start_time": chord.start_time,
                "end_time": chord.end_time,
                "eye_id": int(eye_id),
                "method": args.method,
                "n_samples": len(values),
                "pupil_timestamps": json.dumps(times),
                "pupil_dilation": json.dumps(values),
            })
            summary_rows.append({
                "trial_num": chord.trial_num,
                "chord_num": chord.chord_num,
                "start_time": chord.start_time,
                "end_time": chord.end_time,
                "eye_id": int(eye_id),
                "n_samples": len(values),
                "mean_pupil_dilation": np.mean(values) if values else np.nan,
                "sd_pupil_dilation": np.std(values, ddof=1) if len(values) > 1 else np.nan,
            })
            if not eye_data.empty:
                eye_data = eye_data.copy()
                eye_data["trial_num"] = chord.trial_num
                eye_data["chord_num"] = chord.chord_num
                eye_data["chord_start_time"] = chord.start_time
                eye_data["chord_end_time"] = chord.end_time
                sample_parts.append(eye_data)

    pupil_samples = pd.concat(sample_parts, ignore_index=True) if sample_parts else pd.DataFrame()
    pd.DataFrame(vector_rows).to_csv(out / "chord_pupil_vectors.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(out / "chord_pupil_summary.csv", index=False)
    pupil_samples.to_csv(out / "chord_pupil_samples_long.csv", index=False)

    ratings["sample_time"] = pd.to_numeric(ratings["sample_time"], errors="coerce")
    ratings["chord_num_at_sample"] = pd.to_numeric(ratings["chord_num_at_sample"], errors="coerce")
    ratings["pleasantness_continuous"] = pd.to_numeric(ratings["pleasantness_continuous"], errors="coerce")
    pleasantness = (
        ratings.dropna(subset=["trial_num", "chord_num_at_sample"])
        .groupby(["trial_num", "chord_num_at_sample"], as_index=False)
        .agg(
            n_pleasantness_samples=("sample_time", "count"),
            mean_pleasantness=("pleasantness_continuous", "mean"),
            sample_time_start=("sample_time", "min"),
            sample_time_end=("sample_time", "max"),
        )
        .rename(columns={"chord_num_at_sample": "chord_num"})
    )
    pleasantness.to_csv(out / "chord_pleasantness_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(14, 5))
    for eye_id, data in pupil.groupby("eye_id"):
        data = data.sort_values("pupil_timestamp")
        ax.plot(data["pupil_timestamp"], data["diameter"], linewidth=0.7, label=f"Eye {int(eye_id)}")
    for chord in annotation.itertuples(index=False):
        ax.axvline(chord.start_time, color="grey", alpha=0.35, linewidth=0.5)
        ax.text(chord.start_time, 0.98, str(chord.chord_num),
                transform=ax.get_xaxis_transform(), rotation=90, va="top", fontsize=7)
    ax.set(xlabel="Pupil Capture time (s)", ylabel="Pupil dilation (diameter)",
           title="Pupil dilation by chord")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / "chord_pupil_alignment.png", dpi=180)
    plt.close(fig)

    print(f"Pupil samples mapped: {len(pupil_samples)}")
    print(f"Chord-eye vectors: {len(vector_rows)}")
    print(f"Output folder: {out.resolve()}")
    print("Pleasantness sample_time remains on the PsychoPy trial clock; confirm clock alignment before merging by absolute time.")


if __name__ == "__main__":
    main()
