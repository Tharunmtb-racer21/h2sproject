# SIH168 — 2-Minute Hackathon Demo Script
**Speaker Guide | Timed for 120 seconds**

---

## Opening (0:00 – 0:15) — Hook

> *"What happens to your navigation when GPS disappears? In tunnels, underground parking, bridges — your map freezes. We solved that."*

**[Action]** Dashboard is open, data is loaded, NOT yet playing.

---

## Problem Statement (0:15 – 0:25)

> *"GPS fails in 30% of urban environments. Existing dead reckoning — simple speed × time integration — accumulates errors of hundreds of metres within 30 seconds."*

---

## Show GNSS-Locked Mode (0:25 – 0:35)

**[Action]** Click **Play**

> *"Here is normal GPS navigation. Full satellite lock. Speed, heading, and position from hardware GPS."*

**[Point to]** Green "GNSS LOCKED" status, vehicle trace on map.

---

## Trigger Outage (0:35 – 0:45)

**[Action]** Click **Simulate Outage**

> *"GPS is gone. Completely. Watch — the system automatically switches to AI dead reckoning, using only the phone's IMU sensor."*

**[Point to]** Amber "AI DEAD RECKONING" status. Vehicle position continues updating.

---

## Explain the AI Stack (0:45 – 1:15)

> *"Three innovations make our system accurate:"*

> *"First — a PyTorch neural network trained on real driving data estimates vehicle speed purely from accelerometer and gyroscope signals. No GPS needed."*

> *"Second — NHC: a ground vehicle cannot slide sideways. We enforce this physically to eliminate lateral drift."*

> *"Third — ZUPT: when the car stops at a red light, we detect that using IMU variance alone and zero the velocity — preventing a runaway error."*

> *"These three corrections together reduce 30-second drift from hundreds of metres to under 20 metres."*

---

## Restore GNSS (1:15 – 1:30)

**[Action]** Click **Restore GNSS**

> *"When GPS returns, we don't just switch — we sigmoid-blend smoothly over 2 seconds. No position jump, no discontinuity. The vehicle's path stays coherent."*

**[Point to]** Blending status, smooth convergence on map.

---

## Results Summary (1:30 – 1:45)

> *"Benchmarked on a real-world dataset — IOVNBD recorded from a phone in a moving vehicle:"*
> - *30-second outage: 17 metre mean error*
> - *60-second outage: 27 metre mean error*
> - *GNSS restoration jump: under 5 metres*

---

## Closing (1:45 – 2:00)

> *"This is a fully working, real-time system running on a laptop CPU. No cloud, no external servers, no GPU. The same stack can run on an embedded controller in any vehicle."*

> *"SIH168: AI-ML Based Intelligent Dead Reckoning. Thank you."*

---

## Timing Summary

| Segment | Start | Duration |
|---------|-------|----------|
| Hook | 0:00 | 15s |
| Problem | 0:15 | 10s |
| GNSS Locked Demo | 0:25 | 10s |
| Outage Trigger | 0:35 | 10s |
| AI Stack Explanation | 0:45 | 30s |
| Restoration | 1:15 | 15s |
| Results | 1:30 | 15s |
| Close | 1:45 | 15s |

---

## Key Numbers to Memorize

- **17 m** — 30-second outage error (benchmark)
- **< 5 m** — restoration position jump
- **5 sessions** — training dataset size
- **0** — reference GPS used during dead reckoning
- **CPU only** — no GPU required

---

*SIH168 | Demo Script v1.0*
