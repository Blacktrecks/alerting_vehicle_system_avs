# AVS: design fix and hardening prompt

How to use: paste the **Header** (context, rules, baseline, findings) plus **one phase at a time** into your coding
agent, in a fresh session per phase. Do not paste all phases at once: the agent drifts on long tasks.

---

## Header (always paste)

You work in the repository `alerting_vehicle_system_AVS` (Proximity and Impact Warning System; course "Proiectarea
sistemelor incorporate", lab L5 RTE development). Read `AGENTS.md` first and keep every rule in it: English only,
layer dependency rules (enforced by `tests/test_layers.py`), naming conventions, no renaming of MCD functions, never
weaken a test. Section 9 of `AGENTS.md` ("known defects") is already fixed: do not redo it. This prompt adds the work below.

### Working rules
1. Test first. For every finding: write the test, run it and confirm it FAILS for the stated reason, then fix the code
   with the smallest change that makes it pass. Say in your report that you saw it fail.
2. After each phase run all three commands; all must pass before you commit:
   `MCD_SIMULATE=1 python -m mcd.test` / `MCD_SIMULATE=1 python -m rte.test` / `MCD_SIMULATE=1 DJANGO_DEBUG=1 python manage.py test`.
3. One commit per phase: `phaseN: <what>`.
4. If you add or remove a public `RTE_*` function: update `docs/rte_api.md` (table, group counts, total), the function-count
   assertion in `rte/test.py`, and `AGENTS.md` section 6, all in the same commit. Otherwise do not change the public RTE API.
5. No new dependencies. No Romanian text. Do not open or print whole files you do not need.
6. If a test fails twice, stop and report the failing output instead of looping.
7. Final reply of each phase: at most 15 lines: what changed, the three test results (counts), open issues. No file contents.

### Baseline (measured on the delivered zip; do not re-verify)
- All suites green: `manage.py test` = 345 tests OK (4 hardware tests skipped), `rte.test` = 80 OK. 26 public RTE functions.
- Mutation check (bugs injected into a copy, then the tests run): `rte/__init__.py` 19 of 25 caught, `app/` 24 of 25 caught.

### Findings (verified by running code, ordered by importance)
- **F1 The virtual functional bus is decorative.** The RTE signals exist, but the app modules do not exchange data through
  them. `app/node.py` keeps shadow copies (`NodeRuntime.distance_cm / level / impact`, lines 39-41) and passes them to
  `ALR_vStep(manager, now_ms, level, impact, distance_cm, ...)` as arguments. `ALR` and `RPT` never call any
  `RTE_u*Read*`. `RTE_u8ReadImpact` has no production caller at all. Four public RTE functions are never called by
  `app/`, `web/` or `sim/`: `RTE_u8GetDistanceSensorStatus`, `RTE_u8GetTick1s`, `RTE_u8GetVibrationState`, `RTE_u8ReadImpact`.
  `docs/rte_api.md` (line 42) claims "ALR / RPT / the web views read them": that is false today.
- **F2 Hardware is not owned by one thread.** `web/api.py:outputs_off()` (line 105) calls `NODE_vClearPulses()`
  (`app/node.py:163`) which calls `ALR_vShutdown()` and so `RTE_vSetBuzzer(0)` / `RTE_vSetLed(0)` from the web request
  thread (confirmed: thread name `web-request-thread`). This contradicts `AGENTS.md` section 6 and the docstring of `web/api.py`.
- **F3 `RTE_vInit` is not exception-safe.** If a radio `connect()` raises (for example `OSError`), `RTE_vInit` propagates
  after IOC and SCHED were started and both links were assigned, but `_initialized` stays False. `NODE_vStart` is called
  from `web/apps.py:ready()`, so one unlucky USB error stops the whole Django app from booting. Also `rte/__init__.py:90`
  resets `_signals` without holding `_sig_lock`.
- **F4 Private access.** `rte/sim_support.py:44` returns `rte._mesh, rte._zigbee`. Nothing outside `rte/` may use `rte._*`.
- **F5 Tests that cannot fail in specific cases** (surviving mutants):
  - `rte/test.py:458,463` build the text boundary from `rte.RTE_MESH_TEXT_MAX_BYTES` itself, so changing the limit 200 -> 201
    still passes. No test uses a multi-byte character, so counting characters instead of UTF-8 bytes also passes.
  - Removing the argument check in `RTE_vSetBuzzer` or widening the kind range in `_send_alert` passes, because IOC / SDC
    validate again. The RTE contract is therefore not tested at the RTE level.
  - Safety invariant untested: removing `ALR_vShutdown()` from the `except` branch of `app/node.py:_loop` (line 111) passes.
  - `DocumentationTests` only compare the `###` headings with the function list; the parameter, type, interval and
    reentrant cells are never checked against the code.
- **F6 Lab alignment.** The lab asks for a unit file (`unit.c`); here it is `rte/test.py`, with no per-function PASS/FAIL
  report. The lab's function tables use separate Name / Type / Description / Interval columns for parameters and return
  value; `docs/rte_api.md` folds them into one cell.

---

## Phase 1: make the signal bus real (F1)

Goal: application modules communicate only through RTE signals, and no public RTE function is dead.

1. `ALR_vStep` reads `RTE_u8ReadAlertLevel()`, `RTE_u8ReadImpact()` and `RTE_u16ReadDistanceCm()` itself; remove the
   `level`, `impact`, `distance_cm` parameters of `ALR_vStep`. Keep the pure `AlertManager.update(now_ms, level, impact, distance_cm)`.
2. `NodeRuntime` loses `distance_cm`, `level`, `impact`; `NODE_tGetStatus()` and the RPT sample read the RTE signals.
3. Give each dead function a real job (do not delete them):
   - `RTE_u8GetDistanceSensorStatus`: `PRX_vStep` uses it as the validity flag; `RTE_DISTANCE_INVALID` stays the value on the bus.
   - `RTE_u8GetVibrationState`: published in `NODE_tGetStatus()` and shown on the dashboard Tests page as "vibration input level".
   - `RTE_u8GetTick1s` + `RTE_u8GetMeshStatus` + `RTE_u8GetZigbeeStatus`: once per second NODE compares the link status with the
     previous one and logs "mesh link up/down" and "zigbee link up/down" in the event log.
   - `RTE_u8ReadImpact`: read by ALR (item 1).
4. `tests/test_layers.py`: add a test that fails when any public `RTE_*` function has no caller in `app/`, `web/` or `sim/`.
5. `docs/rte_api.md`: replace the vague sentence by a table `Signal | Writer | Readers`, and add a test that parses it and
   checks with `ast` that every listed writer and reader module really calls the function.

Acceptance: a test drives `ALR_vStep` with NO signal arguments, only by calling `RTE_vWrite*` first, and asserts the buzzer pin,
the LED pin and the packets sent; the dead-API test passes; all suites green.

## Phase 2: one thread owns the hardware (F2)

1. Add `NODE_vRequestOutputsOff()`: sets a flag that the runtime thread consumes at the start of its next step (at most 100 ms
   later). `web/api.py:outputs_off()` calls only this. Fallback: if the runtime thread is not running, switch off directly.
2. Test: patch `app.alr.RTE_vSetBuzzer` and `RTE_vSetLed` with spies that record `threading.current_thread().name`, call
   `web.api.pulse()` and `web.api.outputs_off()` from a plain thread, and assert every recorded call came from `node-runtime`.
3. Test with `ast`: `web/` and `sim/` never call `RTE_vSetBuzzer` or `RTE_vSetLed`.

Acceptance: the emergency stop still turns both outputs off within 150 ms in a test with the real runtime thread.

## Phase 3: robust init (F3, F4)

1. `RTE_vInit`: each `connect()` in its own `try/except`; a failed radio keeps its link object, reports status 0 and keeps
   the error text for `devices.radio_info()`; init continues. If `IOC_vInit` or `SCHED_vStart` raises, stop what was
   started, leave `_initialized = False` and re-raise. Hold `_sig_lock` when resetting `_signals`.
2. Tests (use `unittest.mock.patch`): `MeshtasticLink.connect` raises `OSError` -> `RTE_vInit` returns, buzzer and LED are 0,
   mesh status 0, zigbee status 1; `IOC_vInit` raises -> nothing left running and a second `RTE_vInit` works.
3. `tests/test_layers.py`: no file outside `rte/` references a name that starts with `rte._`.

## Phase 4: tests that can fail (F5)

1. `rte/test.py`: use the literal numbers: 200 bytes accepted, 201 rejected. Add `"é" * 100` (200 bytes) accepted and returns
   200, `"é" * 101` (101 characters, 202 bytes) rejected.
2. RTE contract tests use spies: with `patch("rte.IOC_vSetOutputPort")` and a patched `send_alert`, invalid arguments must
   leave them uncalled (`assert_not_called`). A removed RTE check must now fail a test.
3. Test for the safety invariant: start the real runtime thread, make `NODE_vStep` raise, and assert both GPIO pins are 0
   and a "step error" event is logged.
4. `DocumentationTests`: parse every function table in `docs/rte_api.md` and compare parameter names with
   `inspect.signature`, the return type with the name prefix (`v` void, `u8`, `u16`, `t`), and the constants listed in the docs
   with the code. Reentrant must be Yes or No.
5. `scripts/mutation_check.py` (standard library only): copies the project to a temp folder, applies at least 25 mutants to
   `rte/__init__.py` and 20 to `app/*.py` (one at a time), runs the matching tests, prints killed / survived, exits 1 if a
   non-equivalent mutant survives. List known equivalent mutants with a one-line reason each.
6. Rename `tests/test_phase1.py` to `tests/test_ioc_rte_outputs.py` and delete its `test_app_import_rule` (duplicate of `test_layers.py`).

Acceptance: `python scripts/mutation_check.py` exits 0.

## Phase 5: lab L5 deliverables (F6)

1. Decorator `@covers("RTE_vSetBuzzer", ...)` on tests in `rte/test.py`. A test fails if a public function has no covering test.
2. `rte/unit.py`: `python -m rte.unit` runs the suite and prints one row per public RTE function
   (`name | tests | PASS/FAIL`), writes the same table to `docs/unit_report.md`, exits 1 on any failure.
3. `docs/rte_api.md`: per function a table with Name, Description, a Parameters table (Name | Type | Description | Interval),
   a Return table (Type | Description | Interval) and Reentrant, like the lab. Keep the `### \`RTE_x\`` headings.

## Phase 6 (optional, after 1-5 are green): make it useful

1. Persistent log: append every event and every 60 s report as one JSON line to `logs/events.jsonl` (rotate at 1 MB, keep 3);
   endpoint `GET /api/log/` downloads it. Tests use a temp folder. It is the evidence for the lab report and survives a reboot.
2. `python manage.py selftest`: with a fake clock and simulation only, runs the scenarios 160 -> 20 cm approach, three knocks,
   a remote alert over Zigbee and over LoRa Meshtastic, a replayed packet, a packet with a wrong key, and a forced step
   error. Prints rows 1-9 of the acceptance table in `docs/testing.md` as PASS/FAIL and writes `docs/selftest_report.md`.
   Must finish in under 10 s without hardware.
3. V-model traceability: `docs/traceability.md` (Requirement ID -> design element -> test -> status). Requirements REQ-01...
   come from `AGENTS.md` sections 6-7. Tests carry `# REQ-xx` in their docstring; a test fails when a REQ has no test or a test
   cites an unknown REQ.

---

## Definition of done
- Three test commands green; `python scripts/mutation_check.py` exits 0; `python -m rte.unit` prints 26 PASS rows.
- No public `RTE_*` function without a production caller and a covering test; docs table count equals the code.
- `README.md` and `docs/testing.md` show the real test counts and the results-log row is filled in.
