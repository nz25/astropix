# The light source

**Run this before the first frame of any session that needs light.** Cap-on sessions — the bias
sweep, the dark bound — do not run it and should not adapt it.

It is three items, and it used to be eight. The other five left because they are enforced by code
that refuses to proceed rather than by a human remembering: `asi.open_camera` raises naming both
the ASIAIR and the missing Windows driver as the two causes of a camera that is not there,
`asi.neutralise_white_balance` runs on every open, `asi.cool_to` holds its own settle window and
carries the power-cycle rule, and `asi.set_roi` rejects an odd ROI before the Bayer phase can
shift. Each numbered protocol states its own gates in full. **What is left here is the part no
code can check: a panel, a tablet's settings, and a measurement that has to be made with the
camera.**

The panel is an iPad running `grey-patch.html`. `patch-server.py` serves it over the LAN and lets
the capture side set the grey level, so an attenuation sweep costs no trips to the tablet — and
the page reports its own wake-lock state rather than implying it holds one.

---

## 1. Start the light source ten minutes early

Power the iPad, set brightness to **100%**, open `grey-patch.html`, and then **leave it alone for
ten minutes** before capturing anything.

**Status: a precaution against an untested hypothesis, not a verified fact.** L31 records an
unexplained **1.79%** frame-to-frame instability at gain 100 (against 0.011% at gain 200) that the
retired project could not account for, on a timescale of tens of seconds. LED backlights dim as
they warm, and a panel at full brightness reaches thermal equilibrium over minutes — which fits
the timescale and survives the "settling" check that was run, because re-running minutes later
does not help if the panel is still heating.

It costs ten minutes of a session that runs for hours. **If the L31 stability trace shows a flat
line from cold, delete this item** — do not keep a ritual whose reason has been falsified.

## 2. Settle the iOS settings

Off, all three, every session — each one changes the light mid-run with nothing in the data to
show it: **Auto-Brightness** (Accessibility → Display & Text Size), **Auto-Lock** set to Never
(Display & Brightness), **Night Shift** (Display & Brightness).

Auto-Lock is the one that matters most and the one the page cannot help with. `grey-patch.html`
requests a Screen Wake Lock, but that API exists only in a secure context: served over plain
`http://` on the LAN it is unavailable, the page says so in as many words, and **Auto-Lock set to
Never is then the only thing keeping the panel lit.**

## 3. Measure the attenuation — never predict it

Measure the flux and solve for the saturating exposure at every gain from the measured value. Do
not extrapolate from a per-sheet figure: **stacked diffusers give diminishing returns** — 1.68×,
1.47×, 1.29×, 1.24× as sheets are added — and **grey level is exhausted below about 25% of full
scale** because the backlight leaks through a black LCD.

This is a measurement with the camera, not a lookup, and it is the first section of the session's
own notebook rather than an item to tick. It ends with a **configuration** — grey level and sheet
count — and the flux that pair produced.

---

## Record for the session

Ambient temperature, grey level, sheet count, ROI, gain range, offset, and the measured flux from
item 3. **The attenuation is valid only while the bench is undisturbed**, and undisturbed includes
nobody having moved the camera off the panel.
