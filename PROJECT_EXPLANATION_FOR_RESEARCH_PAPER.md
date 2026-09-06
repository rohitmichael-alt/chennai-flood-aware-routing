# Project Explanation for the Research Paper

## Short Explanation

The project studies how Chennai road routes should change when flooding, incidents, and congestion alter road capacity. Stage 1 uses Dijkstra; a synthetic prototype can use CCH. The planned Chennai implementation will use CCH only after Stage 6 validation, while the certificate decides whether its synchronized metric must be refreshed.

## What Is Implemented?

### Stage 1

- small Chennai OSM road graph;
- OpenCity 2015 historical flood hotspots;
- CRS-safe road mapping;
- one controlled hard closure on a real mapped edge;
- effective capacity, BPR, and before/after Dijkstra routes.

### Preliminary Routing-Method Experiment

- exact NetworkX Dijkstra reference engine;
- native RoutingKit CCH engine;
- versioned integer metrics and keyed-edge paths;
- certificate-gated refresh controller;
- eager-refresh baseline;
- synthetic monotone and mixed-update experiments;
- uncertainty, critical-facility/population, partial-compliance, and road-criticality methods;
- 45 passing tests.

## What Finds the Path?

Stage 1 uses Dijkstra. The preliminary synthetic experiment supports either Dijkstra or CCH. CCH is the planned Chennai path engine after topology, turn, closure, and quantization validation.

- Dijkstra is the correctness baseline.
- ALT-guided bidirectional A* is an unimplemented planned comparator.
- The certificate is not another path algorithm; it controls CCH metric refresh.

## Three-Road Example

Three parallel roads initially cost:

```text
A = 5 minutes
B = 6 minutes
C = 8 minutes
```

CCH chooses A. With a 5% tolerance, the certified limit is 5.25 minutes.

- If projected traffic raises A to 5.2, reuse A without refreshing CCH.
- If A rises to 5.8, refresh CCH.
- If A rises to 7.0, refreshed CCH selects B at 6.0.

The proof works because all pending weights increased. A decrease or reopening can invalidate the old lower bound and forces refresh.

## Is This Novel?

The certificate principle is not new. CPD-Search, truncated/lazy incremental search, and CERT-FLOW contain close lower/upper-bound ideas.

The defensible contribution is:

> A reproducible Chennai-oriented evaluation designed to apply the certificate as a CCH refresh gate and separate routing computation from the traffic effects of stable, projected-load-aware route adoption under compound disruption.

This is integration/evaluation novelty, not a new shortest-path algorithm.

## Preliminary Evidence

In one synthetic experiment with 5,000 CCH queries:

- monotone updates avoided 94 of 100 eager update refreshes;
- mixed updates avoided 14 of 100;
- no route-quality certificate violations were observed;
- no exact mismatch occurred after refresh.

These results are not yet Chennai/SUMO outcomes.

## Additional Evaluation Factors

The paper adds:

1. uncertainty and data-freshness sensitivity;
2. critical-facility accessibility;
3. population-weighted access loss;
4. partial route-guidance compliance;
5. facility-oriented road criticality.

They are evaluation objectives, not arbitrary route penalties.

Historical Chennai evidence can support a retrospective methods submission,
depending on validation and venue. Existing hotspot/hazard layers do not form
an observed road-state replay, so the correct framing is
historical-evidence-conditioned scenario reconstruction with simulated traffic.
The project must say “designed for near-real-time operation,” not “validated
live Chennai routing.”

## What Remains?

- reproducible dated Chennai graph;
- rainfall/flood road-state model;
- Chennai SUMO calibration;
- production CCH topology, ordering, turn, closure, and quantization validation;
- stable projected-load policy;
- facility/population integration;
- emergency scenario;
- full ablation and statistical evaluation.

## Full Document

See:

- `docs/PROJECT_RESEARCH_AND_EVIDENCE.md`
- `docs/PROJECT_RESEARCH_AND_EVIDENCE.docx`
- `CONTEXT.md`
- `PLAN.md`
