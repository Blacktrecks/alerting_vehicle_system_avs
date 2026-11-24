# Plan

## G1 · Meshtastic setup guide as markdown instead of Word — done
*Done when:* docs/meshtastic_setup_guide.md exists with all content from the docx (sections, tables, commands) and is committed

- [x] **T1** Convert docx to markdown
  - check: Every heading, table and code block from the docx dump is present in the md file
  - note: verified: every docx paragraph and table cell matched the markdown file; commit b0abd72 contains docs/meshtastic_setup_guide.md

## G2 · Guide covers installing and running the program on Pi4/Pi5, Linux and Windows — done
*Done when:* docs/meshtastic_setup_guide.md has a verified install/run section for Pi4/Pi5, Linux and Windows, committed

- [x] **T2** Write the install/run section and commit
  - check: Every claim in the new section matches code I read this session (mcd/config.py, mcd/pcs.py, requirements, README); committed
    - evidence: commit `a9c6a9d`

## G3 · Standalone setup guide for Linux, Pi and Windows, with the Linux path tested — done
*Done when:* docs/setup_guide.md exists with Linux, Pi4/Pi5 and Windows install-and-run steps; the Linux path is verified by running the project tests on this machine; committed

- [x] **T3** Write docs/setup_guide.md and commit
  - check: Linux path tested here (345 tests OK, Python 3.14.4); guide has numbered steps for Linux, Pi4/Pi5, Windows; committed
    - evidence: commit `f342ab6`

## G4 · Phase 1: make the signal bus real (F1) — done
*Done when:* Phase 1 done: ALR_vStep and NodeRuntime read only RTE signals; every public RTE_* has a real caller; test_layers has the dead-API test; docs/rte_api.md has a Signal|Writer|Readers table with an ast-parsing test; all three suites green; comm

- [x] **T4** Write the failing tests (test-first)
  - check: New tests written first and confirmed to FAIL for the stated reasons (dead-API test, ALR_vStep-no-args acceptance test, rte_api.md table parser test)
  - note: verified: ran the new tests before any code change — dead-API test lists RTE_tGetMeshAlert, RTE_tGetZigbeeAlert, RTE_u16SendMeshAlert, RTE_u8GetDistanceSensorStatus, RTE_u8GetTick1s, RTE_u8GetVibrationState, RTE_u8ReadImpact as dead; 8 failures + 1 error in the phase-1 tests for the stated reasons
- [x] **T5** Implement the app changes (alr, node, prx, web)
  - check: ALR_vStep reads signals; PRX validity flag; NODE vibration level + link up/down logging; dashboard Tests page shows vibration input level; tests now pass
    - evidence: test `MCD_SIMULATE=1 manage.py test: 355 tests OK (skipped=4); test_phase1_f1 OK(9); mcd OK, rte OK`
- [x] **T6** Docs table + full run + commit
  - check: docs/rte_api.md Signal|Writer|Readers table; ast test passes; all three suites green; single commit 'phase1: ...'
    - evidence: commit `a8b817e`

## Log
- 2026-11-21 18:30 goal G4 added: Phase 1: make the signal bus real (F1)
- 2026-11-21 18:32 task T4 added: Write the failing tests (test-first)
- 2026-11-21 18:32 task T5 added: Implement the app changes (alr, node, prx, web)
- 2026-11-21 18:32 task T6 added: Docs table + full run + commit
- 2026-11-21 18:33 4 -> doing
- 2026-11-21 18:34 4 -> done: verified: ran the new tests before any code change — dead-AP
- 2026-11-21 18:34 5 -> doing
- 2026-11-24 10:19 6 -> doing
- 2026-11-24 10:19 T5 evidence: test MCD_SIMULATE=1 manage.py test: 355 tests
- 2026-11-24 10:19 T6 evidence: commit a8b817e
- 2026-11-24 10:19 5 report written
- 2026-11-24 10:19 6 report written
- 2026-11-24 10:19 5 -> done
- 2026-11-24 10:19 6 -> done
- 2026-11-24 10:19 goal G4 done
