# Plan

## G1 · Execute the AGENTS.md open-work list (items 1-6) on branch fix/l5-hardware-hardening — active
*Done when:* All 6 open-work items committed one by one, each with a test that failed before; full suite green at the end.

- [x] **T1** Open work 1: replay-guard resync after sender reboot
  - check: new test fails before change, passes after; full suite green
    - evidence: commit `fa2204f`
- [x] **T2** Open work 2: GPIO chip label parsing in mcd/pcs.py _(needs T1)_
  - check: test with both tuple orders passes; full suite green
    - evidence: commit `5bc4f31`
- [x] **T3** Open work 3: ultrasonic echo timing (kernel timestamps or median of 3) _(needs T2)_
  - check: timing test passes; full suite green; sim path and existing tests kept
    - evidence: commit `457f650`
- [x] **T4** Open work 4: non-blocking radio connect in rte.RTE_vInit / web/apps.py _(needs T3)_
  - check: timeout test passes; full suite green
    - evidence: commit `8826574`
- [x] **T5** Open work 5: docs/hardware.md fixes (pull-down, CP210x/CH340, SW-420 polarity) _(needs T4)_
  - check: grep the three notes in docs/hardware.md
    - evidence: commit `e3b79e3`
- [ ] **T6** Open work 6: repo hygiene for the setup guide docx and zip _(needs T5)_
  - check: git status clean; .gitignore or tracked decision documented
    - evidence: commit `98a0b93`

## Log
- 2026-11-24 10:53 3 -> doing
- 2026-11-24 10:57 3 report written
- 2026-11-24 10:57 task T4 added: Open work 4: non-blocking radio connect in rte.RTE_vInit / w
- 2026-11-24 10:57 T3 evidence: commit 457f650
- 2026-11-24 11:10 4 report written
- 2026-11-24 11:10 task T5 added: Open work 5: docs/hardware.md fixes (pull-down, CP210x/CH340
- 2026-11-24 11:10 T4 evidence: commit 8826574
- 2026-11-24 11:11 5 report written
- 2026-11-24 11:11 task T6 added: Open work 6: repo hygiene for the setup guide docx and zip
- 2026-11-24 11:11 T5 evidence: commit e3b79e3
- 2026-11-24 11:12 6 report written
- 2026-11-24 11:12 3 -> done
- 2026-11-24 11:12 4 -> done
- 2026-11-24 11:13 5 -> done
- 2026-11-24 11:13 T6 evidence: commit 98a0b93
