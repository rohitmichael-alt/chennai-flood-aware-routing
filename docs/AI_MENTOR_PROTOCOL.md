# AI Mentor Protocol — Certificate-Gated Chennai Routing

This file is the **handoff contract** for any later AI. It is not a completed paper and it is not permission to invent missing data.

**Student-stated local clone (unverified by the writing agent):**  
`C:\Users\rohit michael\Documents\researchwork\chennai-flood-routing`

**GitHub:** https://github.com/rohitmichael-alt/chennai-flood-aware-routing

**Goal of the project:** a **research paper** (and a separate DAA assignment on another branch). Claims must match evidence. If a number is not observed, published, estimated with a recorded method, or an explicit scenario parameter, it is **unavailable** — do not impute it.

---

## 0. Stop and answer these questions before executing Stages 3–10

The writing agent does **not** know the student’s answers. Do not guess.

1. **Which Git line is authoritative for the next run?**  
   This checkout’s paper branch treats Stages 3–6 as PENDING.  
   Branch `cursor/stage-execution-plan-8597` (PR #3) already recorded Stages 3–6 as **PASS WITH LIMITATIONS** / missingness.  
   Those large GraphML/PBF/SUMO files are **gitignored**; only JSON/PNG evidence was committed. Re-running is required unless the student’s laptop still has `data/`.

2. **Is the deliverable the research-and-evidence document, the DAA Word file, or both?**  
   `docs/PROJECT_RESEARCH_AND_EVIDENCE.md` is the research packet on this line.  
   `docs/DAA_ASSIGNMENT.md` exists on the stage-execution branch only.  
   Student named on the DAA file: Rohit Michael Raj, 24BCE5108, VIT Chennai.

3. **Target venue and claim strength?**  
   Integration/evaluation paper vs coursework write-up. That choice changes whether SYNTHETIC SUMO demand is acceptable as a result or only as a limitation.

4. **Credentials?**  
   Official IMERG and SRTM/NASADEM need Earthdata. The documented no-key core is Open-Meteo ERA5 + OSM + OpenCity. Do not use paid APIs as if they were the reproducible core.

5. **Locked study boundary?**  
   PR #3 used Greater Chennai Corporation 2022 wards (OpenCity resource `e90176d4-319a-45bd-918e-ecce4f048c4d`) and Geofabrik `india-260901.osm.pbf`. Re-justify or reuse; do not silently pick a new bbox.

6. **Stage 6?**  
   An earlier instruction on the paper agent was “no need to do Stage 6.” A later instruction asked for stages 0 through end. The student must restate which rule wins. PR #3 already ran inertial CCH vs Dijkstra with limitations (SCENARIO 30 km/h where maxspeed is missing; turns not modelled).

Until (1)–(6) are answered in writing in this file’s “Student decisions” section below, **do not start Stage 3+ as if the answers were known.**

### Student decisions (fill before Stage 3+)

| Question | Answer (student or later agent, dated) |
|---|---|
| Authoritative git line | _unanswered_ |
| Deliverable set | _unanswered_ |
| Venue / claim strength | _unanswered_ |
| Earthdata / extra credentials | _unanswered_ |
| Study boundary | _unanswered_ |
| Stage 6 in or out | _unanswered_ |

---

## 1. Prompt to give the critic / executor AI

Copy everything in this section as the system or first user message.

```text
ROLE
You are three people in sequence, never a co-author who wants the paper to “look good”:

A) Research-integrity officer. Fail any sentence that calls a certificate new, calls
   historical flood live, calls SUMO observed Chennai traffic, or treats a silent
   default as a measurement.

B) Independent methods reviewer (transportation science / experimental algorithms).
   Ask: what claim is supported by which artifact? Is the work paper-worthy at the
   stated venue, or only a prototype report?

C) Reproducibility engineer. Re-run or re-check commands. If you cannot reproduce
   a number, the number is not a result.

PERSONA RULES
- Dijkstra is the correctness oracle.
- CCH is the (optional) path engine.
- CLMS / the certificate controller is a refresh gate, not a shortest-path algorithm.
- BPR is a route-cost model; SUMO (when present) is the realized-traffic model.
- You may not “fix” a gap by inventing speeds, capacities, OD matrices, flood depths,
  compliance rates, ambulance AVL, or signal preemption.
- You may label a value SCENARIO or UNAVAILABLE.
- You may run a sensitivity sweep over a declared range.
- You may not average those into a single “Chennai calibration” without a cited method
  and held-out check.

MANDATORY READING ORDER (do not skip)
1. docs/AI_MENTOR_PROTOCOL.md          (this contract)
2. CONTEXT.md
3. PLAN.md
4. README.md
5. docs/PROJECT_RESEARCH_AND_EVIDENCE.md
6. STAGE1_HANDOFF.md                   (historical; its “DONE” is not publication-complete)
7. PROJECT_EXPLANATION_FOR_RESEARCH_PAPER.md
8. data/README.md, scripts/README.md, tests/README.md
9. docs/evidence/*.json that exist on the current checkout
10. Then the code: src/, scripts/, tests/, pyproject.toml, .gitignore
11. If the student authorized the other line: git show / checkout
    origin/cursor/stage-execution-plan-8597 and read its PLAN.md, DAA file,
    and docs/evidence/STAGE{3,4,5,6}_*.json

CRITICAL METHOD
For every stage 0–10:
- List files that implement it.
- List artifacts that exist in git vs only on disk vs missing.
- Classify every scientific constant: OBSERVED / PUBLISHED / ESTIMATED /
  SCENARIO / UNAVAILABLE.
- Quote the claim the paper currently makes and mark SUPPORT / OVERCLAIM / SILENCE.
- Decision: PASS | PASS WITH LIMITATIONS | BLOCKED | FAIL.
A stage is not complete because a function exists.

ETHICS
- Do not scrape or fabricate personal location traces.
- Facility catalogues are locations, not capacity or trauma capability.
- Population surfaces are not equity analysis.
- Do not present coursework as a peer-reviewed result or vice versa.
- Keep student identity consistent with the document being written.

EXECUTION ORDER AFTER THE AUDIT
Only if Student decisions in docs/AI_MENTOR_PROTOCOL.md are filled:
Stage 0 docs alignment
→ 1 (publication-grade demo evidence or keep labelled demo)
→ 2 (already synthetic; do not over-claim)
→ 3 dated graph
→ 4 explained road states
→ 5 SUMO with demand class labelled
→ 6 city CCH if in scope
→ 7 reservations (filter already partial)
→ 8 Chennai facilities/population
→ 9 emergency scenario
→ 10 evaluation + manuscript whose claims match generated evidence

If a gate FAILS or is BLOCKED, stop that chain. Do not write Stage 10 “results”
from missing Stages 3–9.

OUTPUT
1. A written audit (update this protocol’s audit log).
2. Code/doc changes only where they remove overclaims or implement a gated task.
3. Tests.
4. Regenerated Word/PDF only after markdown claims match code.
```

---

## 2. Why this role (brainstorm, condensed)

| Candidate role | Why rejected or kept |
|---|---|
| Helpful co-author | Will paper over missing data. Reject as primary. |
| “Senior PhD student who believes in the project” | Same risk. |
| DAA grader only | Would ignore publication integrity and prior-art claims. Use as extra pass on the DAA file only. |
| Integrity officer + methods reviewer + repro engineer | Kept. Matches “no assumptions” and “paper worthy.” |

There is **no Claude-plugin “superpower” or mastermind skill** in the cloud environment that wrote this file. Cursor skills present there were environment/setup, canvas, and walkthrough artifacts — none replace a methods review.

---

## 3. Integrity rules (never weaken)

1. Never call the certificate principle new. Prior art includes CPD-Search, truncated incremental search, LazySP, CERT-FLOW, CCH, CATCHUp.
2. Never call historical OpenCity flood **live**.
3. Never call SUMO **observed** Chennai traffic.
4. Never claim city-scale outcomes from the 200-node synthetic experiment.
5. Never compare CCH and Dijkstra traffic outcomes under different policies.
6. Rainfall and elevation are not street flood depth.
7. Facility access is an evaluation outcome, not an arbitrary route penalty.
8. Report negative results (example already in the paper: mixed-update lazy CCH can be slightly slower than eager CCH in one prototype run).

---

## 4. What “paper worthy” means here

The research document already states the defensible contribution: a **Chennai-oriented integration and evaluation framework**, not a new algorithm.

**Currently supportable (this paper-branch checkout, Stage 2 JSON committed):**

> On deterministic synthetic fixed-topology workloads, the monotone metric certificate returned routes within its declared represented-cost bound, matched exact routing after refresh, and reduced eager metric refreshes for both Dijkstra and CCH adapters.

**Not supportable until later stages produce versioned artifacts:**

- improved Chennai travel time or emergency response;
- operational real-time flood routing;
- city-scale CCH performance as a general fact;
- calibrated BPR/flood-capacity physics;
- causal claims from one-edge Stage 1 demos.

A honest paper can still be written as **retrospective scenario reconstruction + synthetic method evidence**, if every limitation stays in the abstract/results, not only in an appendix.

---

## 5. Git lines (do not collapse them)

| Line | Branch | PR | What it contains |
|---|---|---|---|
| Paper / professor packet | `cursor/professor-research-evidence-8597` and follow-on `cursor/model-pathways-audit-8597` | #2, #4 | Research md/docx/pdf; Stage 1–2 code; pathway glue; **Stages 3–6 not in this tree** |
| Stage execution | `cursor/stage-execution-plan-8597` | #3 | Stage 3–6 scripts, evidence JSON, DAA assignment; graph/SUMO binaries gitignored |
| Default | `master` | — | Also has frontend/presentations; do not treat slides as evidence |

`.gitignore` drops `data/raw/*`, `data/processed/*`, `outputs/*`. Publication graphs are not on GitHub unless someone changes that policy with LFS or a documented external store.

---

## 6. Stage contract (0–10)

Classification used below is for **this paper-branch checkout** unless noted as PR #3.

### Stage 0 — Repository and claim alignment

**Goal:** One architecture, one claim boundary, tests that documents exist.  
**Done here:** package layout, `CONTEXT.md` / `PLAN.md` / tests.  
**Defects a critic must catch:** `STAGE1_HANDOFF.md` still says Stage 1 is complete in a stronger sense than `PLAN.md` (“DONE WITH LIMITATIONS”). `CODEX_SETUP_PROMPT.md` is historical. Two PLAN.md files exist across branches.  
**Exit:** Required-reading list agrees; no document says Stage 3 is both PENDING and finished without naming the branch.

### Stage 1 — Historical flood-to-road demonstration

**Goal:** Show OSM + OpenCity hotspot → nearest road → controlled BLOCKED edge → Dijkstra before/after.  
**Code:** `src/chennai_routing/stage1_poc.py`, `data/flood.py`, `data/osm.py`, `preprocessing/geospatial.py`, `scripts/run_stage1_poc.py`, `tests/test_stage1_poc.py`.  
**Evidence on git:** fixtures/tests; run outputs gitignored. Handoff records a previous run (327 flood points, one-edge OD).  
**Classified constants:** 30 km/h missing speed = SCENARIO; capacity 1200 and flow 600 = SCENARIO; 150 m snap = SCENARIO; BLOCKED on a mapped edge = demonstration overlay, not 2015 observed closure of that OSM way.  
**Exit for a paper figure:** dated OSM extract, checksums, config, and outputs **versioned or archived**, not only a live Overpass query.  
**Do not:** describe it as congestion-calibrated routing.

### Stage 2 — Certificate + engines (synthetic)

**Goal:** Engine-neutral snapshots, Dijkstra oracle, optional `routingkit-cch`, exact rational ε, eager baseline.  
**Code:** `routing/dynamic.py`, `networkx_engine.py`, `cch_engine.py`, `evaluation/experiments.py`, `scripts/run_certified_lazy_sweep.py`.  
**Committed evidence:** `docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json`. Published 5,000-query table comes from the **sweep** script, not the experiment CLI defaults (100 nodes / 40 epochs).  
**Known limits:** degree ordering; CCH rebuilds metric/query objects; CCH rejects +inf closures; mixed decreases force refresh.  
**Exit:** Keep synthetic. Do not retitle as Chennai.

### Stage 3 — Reproducible Chennai graph

**Goal:** Dated extract, stable keyed arcs, missingness audit, free-flow only where speed is explicit or a **published** rule.  
**This checkout:** PENDING (placeholders in `data/osm.py` / `preprocessing/roads.py`).  
**PR #3 recorded:** 155,345 nodes, 331,545 arcs; Geofabrik india-260901; **325,453 arcs missing maxspeed**; only 6,092 explicit speeds/free-flow times; decision PASS WITH REPORTED ATTRIBUTE MISSINGNESS.  
**Exit:** Graph loads without live OSM; audit JSON; no silent 30 km/h on the publication metric unless labelled SCENARIO and sensitivity-tested.  
**Blocked without:** ~1.7 GB PBF download or a local copy, plus clip tools (osmium/pyrosm as used on PR #3).

### Stage 4 — Explained road states

**Goal:** Timestamped `NORMAL/DEGRADED/SEVERE/BLOCKED` with reason, confidence, expiry. Rain/DEM do not prove flooding.  
**This checkout:** generic lag/error utilities; pathway `ExplainedArcState`; UNKNOWN capacity **raises** (must not silently close).  
**PR #3 recorded:** OpenCity KMLs + ERA5 + coarse DEM + drains; BLOCKED/SEVERE = SCENARIO overlays; conflicts counted.  
**Exit:** Table + mapping rules + claim_limit in JSON.  
**Do not:** write “roads were flooded because rainfall exceeded X” unless a **published** inundation product says so for that geometry and time.

### Stage 5 — Traffic / SUMO

**Goal:** Import Stage 3 graph; demand with a class label; BPR estimate vs SUMO realized time; no double-counting delay.  
**This checkout:** `simulation/sumo.py` placeholder.  
**PR #3 recorded:** OSM netconvert failed on SUMO 1.18; GraphML import; 60 synthetic trips; demand **SYNTHETIC**; no public OD or counts found in that run.  
**Exit:** Feasibility JSON. Calibration to Sashank et al. / Gore et al. only with reproduced numbers and matching units — otherwise cite and keep SYNTHETIC.  
**Blocked without:** SUMO installation and an explicit demand construction method.

### Stage 6 — City CCH

**Goal:** Correctness vs Dijkstra on the Stage 3 graph; ordering; closures; turns or an explicit “turns omitted” limit; break-even.  
**This checkout:** prototype CCH on small graphs only.  
**PR #3 recorded:** inertial CCH; 24/24 unpack matches; 20 scenario closures; turns not modelled; missing maxspeed → SCENARIO 30 km/h for that metric.  
**Exit:** `STAGE6_CCH_RESULTS.json` regenerated on the graph actually used.  
**Skip only if the student writes Stage 6 out of scope** in the decisions table.

### Stage 7 — Stability and projected load

**Goal:** Degradation / min-gain / cooldown; time-binned reservations for compliant vehicles; certificate after reservation updates; compare to independent SP and SUMO periodic reroute.  
**This checkout:** `routing/rerouting.py` filter only. Cooldown does **not** delay degradation or infeasible incumbents. Thresholds are SCENARIO (0.15 / 0.05 / 1 epoch). Reservations unimplemented.  
**Exit:** Reservations with units (PCE / time bin) and a herding metric. No equilibrium claim.

### Stage 8 — Facilities, population, compliance, criticality

**Goal:** Use verified catalogues + population surface; connected/disconnected; p50/p90; seeded compliance; rank directed arcs.  
**This checkout:** `evaluation/metrics.py`, `robustness.py` — generic, no Chennai run. Research doc pins some OpenCity facility KML checksums.  
**Exit:** A Chennai matrix from Stage 3/4 states, not toy graphs only.  
**Do not:** treat a health-centre point as a trauma hospital.

### Stage 9 — Emergency scenario

**Goal:** Priority order: safety/feasibility, deadline slack, bounded external delay, stable ties. No signal preemption claim. No live AVL.  
**This checkout:** `routing/emergency.py` not a completed experiment.  
**Exit:** Secondary scenario with ordinary-user harm reported.

### Stage 10 — Evaluation and manuscript

**Goal:** Baselines, scenarios, ablations, CIs, provenance, negative results; claims = evidence.  
**This checkout:** method tables for Stage 2 only.  
**Exit:** Clean-environment reproduction; Word/PDF regenerated from markdown; abstract does not exceed §17 of the research document unless new artifacts exist.

---

## 7. Code map (this checkout)

| Path | Role |
|---|---|
| `src/chennai_routing/models/pathway.py` | Explained state → BPR ms snapshot |
| `src/chennai_routing/models/capacity.py` | Effective capacity; BLOCKED → 0; UNKNOWN invalid |
| `src/chennai_routing/models/bpr.py` | BPR; zero capacity → inf |
| `src/chennai_routing/routing/quantization.py` | Seconds → integer ms |
| `src/chennai_routing/routing/dynamic.py` | Certificate gate |
| `src/chennai_routing/routing/rerouting.py` | Adoption filter |
| `src/chennai_routing/routing/dijkstra.py` | Stage 1 Dijkstra helpers |
| `src/chennai_routing/routing/networkx_engine.py` | Oracle engine |
| `src/chennai_routing/routing/cch_engine.py` | Finite-integer CCH adapter |
| `tests/test_pathway.py` | Pathway / identity / adoption tests |
| `docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json` | Stage 2 numbers in the paper |

Tests on the writing agent’s last run of this line: **55 passed** with `routingkit-cch` installed.

---

## 8. Ethics and overclaim checklist

- [ ] Abstract uses “synthetic” / “scenario” / “historical evidence” where required.  
- [ ] No live-traffic or live-flood wording.  
- [ ] No new-algorithm wording.  
- [ ] Student name matches the document type (DAA vs research packet).  
- [ ] Checksums and retrieval dates for any committed source.  
- [ ] Missing OSM attributes reported as missing, not filled.  
- [ ] Compliance is a sensitivity knob unless a survey is cited.  
- [ ] Population-weighted loss is not called fairness or equity.  
- [ ] Gitignored outputs are not cited as if they were in the repo.

---

## 9. What the writing agent did **not** do (11 Sep 2026)

- Did not merge PR #3 into this branch.  
- Did not re-download the India PBF or re-run SUMO/CCH at city scale.  
- Did not fill Student decisions.  
- Did not claim the work is submission-ready as a full Chennai evaluation.  
- Did not find Claude-plugin superpowers in that cloud environment.

**Authorized next coding step after decisions are filled:**  
If PR #3 is accepted as the data line → continue **Stage 7** on a branch that contains those scripts **and** a restored `data/` tree.  
If this paper line stays isolated → Stage 3 graph first, then 4–10 in PLAN.md order.  
If Stage 6 remains out of scope → Dijkstra stays the only city engine; say so in the paper.

---

## 10. Audit log

| Date | Agent | Action |
|---|---|---|
| 2026-09-11 | Paper-line agent | Wrote this protocol after a claims-vs-code and cross-branch evidence read. Did not execute Stages 3–10. |
| | | _later agents append here_ |
