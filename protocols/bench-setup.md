# Bench pre-flight

Run this before the first frame of any bench session. It is a sequence of **actions**, not an
explanation: each item cites the `LEGACY.md` entry that justifies it, so the reasoning lives in
one place. When an entry is verified and harvested out of `LEGACY`, replace its citation here
with the destination it landed in.

Items 1–3 can invalidate an entire night's data without announcing themselves. Do them in order
and do not skip them because the last session was fine.

---

## 0. Start the light source ten minutes early

Power the iPad, set brightness to **100%**, open `grey-patch.html`, confirm it reports a Screen
Wake Lock — and then **leave it alone for ten minutes** before capturing anything.

**Status: a precaution against an untested hypothesis, not a verified fact.** L31 records an
unexplained **1.79%** frame-to-frame instability at gain 100 (against 0.011% at gain 200) that the
retired project could not account for, on a timescale of tens of seconds. LED backlights dim as
they warm, and a panel at full brightness reaches thermal equilibrium over minutes — which fits
the timescale and survives the "settling" check that was run, because re-running minutes later
does not help if the panel is still heating.

It costs ten minutes of a session that runs for hours. **If the L31 stability trace shows a flat
line from cold, delete this item** — do not keep a ritual whose reason has been falsified.

## 1. Take the camera away from the ASIAIR, and check the driver

The ASIAIR claims the camera exclusively over USB; with it powered on and the camera attached,
the PC will not see the camera regardless of drivers. Confirm the Windows driver is present, not
just the SDK — the two are separate downloads and the SDK alone gives a state where
`zwoasi.init()` succeeds and `get_num_cameras()` returns 0. **(L02)**

```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_03C3' } |
  Format-Table Status, Class, FriendlyName, Problem, ProblemDescription
```

## 2. Neutralise the white balance, and verify it took

The camera ships `WB_R = 55`, `WB_B = 75`, applied to RAW16 **before the data reaches us**. Set
both to 50 on open, then confirm from the pixels rather than from the setting: on a dark, the
modal step between adjacent distinct values must be **16 on all four CFA channels**. Greens 16
with red at 17/18 and blue at 24 is the fingerprint of white balance still being applied. **(L01)**

Nothing captured before this is fixed is usable. It inflated read noise ~17% at every gain.

## 3. Settle the iOS settings

Off, all three, every session — each one changes the light mid-run with nothing in the data to
show it: **Auto-Brightness** (Accessibility → Display & Text Size), **Auto-Lock** set to Never
(Display & Brightness), **Night Shift** (Display & Brightness). **(L06)**

## 4. Cool, and wait for it to settle

Command the cooler on and confirm it is working **by the temperature trend, not by duty cycle** —
watch for 60 s, falling means it works. `ASI_TEMPERATURE` reads a flat 0 until the cooler is on,
so a reading of 0 on an idle camera is not a fault. Expect about 3 °C/min from ~17 °C ambient.
Require the temperature to hold in band for a continuous settle period before the first frame; a
TEC overshoots and rings. **(L03, L04)**

If the cooler draws nothing at all: a previous hard-killed process can leave the TEC latched off.
**Power-cycle the 12 V, do not debug it.** **(L03)**

Our own archive shows what skipping this costs — 2,132 frames more than 1 °C off setpoint, some
flats commanded −20 °C that read +4.5 °C (`results/frame_index.csv`).

## 5. Set the ROI, and check it is even

Even x origin, y origin, width and height, or the Bayer phase shifts and the colour planes are
not where the header says. The retired sweeps used 1024×1024 at (1408, 568). Gain runs **0–600**,
not 0–400. **(L05)**

## 6. Measure the attenuation — never predict it

Run the flux pre-flight and solve for the saturating exposure at every gain from the measured
value. Do not extrapolate from a per-sheet figure: stacked diffusers give diminishing returns
(1.68×, 1.47×, 1.29×, 1.24× as sheets are added), and grey level is exhausted below about 25% of
full scale because the backlight leaks. **(L07, L08)**

## 7. If the session is a linearity run, shrink the ROI

Illumination varies 3.8% peak-to-peak across 1024×1024, which smears a bend defined as a 1%
departure from a straight line. Central 512 gives 1.25%; central **256 gives 0.53%**. This does
not apply to a PTC, which differences frame pairs and is blind to fixed pattern. **(L09, L12)**

---

## Record for the session

Before capturing, write down: ambient temperature, grey level, sheet count, ROI, gain range,
offset, and the measured flux from item 6. The attenuation ladder is valid only while the bench
is undisturbed, and "undisturbed" includes nobody having moved the camera off the panel.
