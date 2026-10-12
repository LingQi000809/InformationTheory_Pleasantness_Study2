"""scale every chord in every file to the same loudness (TARGET, in LUFS)"""

import glob, os
import numpy as np, soundfile as sf

TARGET = -20                             # LUFS, common level for perception experiments
BEAT, SKIP, RAMP = 60 / 25, 0.15, 0.02   # chord length; skip previous chord's release when measuring; gain ramp (s)
IN, OUT = 'stimuli_wav', 'stimuli_wav_loudness_norm'
os.makedirs(OUT, exist_ok=True)
lufs = lambda s: -0.691 + 10 * np.log10(np.mean(s ** 2, axis=0).sum())   # BS.1770 loudness, without K-weighting

for path in sorted(glob.glob(f'{IN}/*.wav')):
    x, sr = sf.read(path, always_2d=True)
    beat = int(BEAT * sr)
    segs = [x[b * beat + int(SKIP * sr):(b + 1) * beat] for b in range(-(-len(x) // beat))]
    loud = np.array([lufs(s) if len(s) > sr / 2 else np.nan for s in segs])
    chord = ~np.isnan(loud) & (np.arange(len(loud)) != 1)
    gain = np.where(chord, 10 ** ((TARGET - loud) / 20), 1.0)
    for b in np.flatnonzero(~chord)[np.flatnonzero(~chord) > 0]:
        gain[b] = gain[b - 1]                               # silence/partial beat: hold previous gain
    knots = np.ravel([[b * beat, b * beat + RAMP * sr] for b in range(len(gain))])
    vals = np.ravel([[gain[b - 1] if b else gain[0], gain[b]] for b in range(len(gain))])
    y = x * np.interp(np.arange(len(x)), knots, vals)[:, None]
    if np.abs(y).max() > 0.98:
        print(f'WARNING {os.path.basename(path)} would clip at {TARGET} LUFS; lower TARGET')
    sf.write(f'{OUT}/{os.path.basename(path)}', y, sr, subtype=sf.info(path).subtype)
    print(f'{os.path.basename(path):24s} chords {loud[chord].min():6.2f} to {loud[chord].max():6.2f} LUFS -> {TARGET:6.2f} LUFS '
          f'(gains {TARGET - loud[chord].max():+5.2f} to {TARGET - loud[chord].min():+5.2f} LU)')
    loud_out = [lufs(y[b * beat + int(SKIP * sr):(b + 1) * beat]) for b in np.flatnonzero(chord)]
    for b, before, after in zip(np.flatnonzero(chord), loud[chord], loud_out):
        print(f'    {"ref" if b == 0 else f"chord {b - 2:2d}"}: {before:6.2f} LUFS -> {after:6.2f} LUFS (gain {after - before:+5.2f} LU)')
