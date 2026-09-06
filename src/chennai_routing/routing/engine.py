"""Engine-neutral types for exact shortest-path queries on metric snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Hashable, Literal, Mapping, Protocol, TypeAlias


NodeId: TypeAlias = Hashable
EdgeId: TypeAlias = tuple[NodeId, NodeId, Hashable]
Weight: TypeAlias = int | float


@dataclass(frozen=True)
class MetricSnapshot:
    """A complete represented metric for one immutable graph topology."""

    topology_id: str
    version: int
    weights: Mapping[EdgeId, Weight]


@dataclass(frozen=True)
class EnginePath:
    """An exact keyed-edge path for the engine's synchronized metric."""

    nodes: tuple[NodeId, ...]
    edges: tuple[EdgeId, ...]
    cost: Weight


@dataclass(frozen=True)
class EngineQuery:
    """A found path or a proof of unreachability for one metric snapshot."""

    status: Literal["FOUND", "UNREACHABLE"]
    path: EnginePath | None


@dataclass(frozen=True)
class EngineCapabilities:
    """Properties required by the certificate controller."""

    name: str
    exact_for_represented_metric: bool
    supports_positive_infinity: bool
    max_finite_weight: int | None


@dataclass(frozen=True)
class SyncReport:
    """Result of atomically replacing an engine metric."""

    previous_version: int | None
    metric_version: int
    edge_count: int


class ShortestPathEngine(Protocol):
    """Protocol implemented by Dijkstra now and a CCH adapter later."""

    @property
    def topology_id(self) -> str:
        """Return the immutable topology identifier."""

    @property
    def metric_version(self) -> int | None:
        """Return the currently synchronized metric version."""

    @property
    def capabilities(self) -> EngineCapabilities:
        """Describe the engine's represented-metric guarantees."""

    def synchronize(self, metric: MetricSnapshot) -> SyncReport:
        """Atomically replace/customize the represented metric."""

    def query(self, source: NodeId, target: NodeId) -> EngineQuery:
        """Return an exact path for the synchronized metric."""


def _canonical_identifier(value: Hashable) -> object:
    if value is None:
        return ["none", None]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise TypeError("Node and edge identifiers cannot be NaN or infinite.")
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, tuple):
        return ["tuple", [_canonical_identifier(item) for item in value]]
    raise TypeError(
        "Node and edge identifiers must be stable primitive values or tuples "
        f"of stable primitive values; received {type(value).__name__}."
    )


def topology_digest(
    nodes: tuple[NodeId, ...],
    edges: tuple[EdgeId, ...],
) -> str:
    """Return a process-stable, type-tagged topology identifier."""

    canonical_nodes = sorted(
        (
            json.dumps(
                _canonical_identifier(node),
                separators=(",", ":"),
                ensure_ascii=True,
            )
            for node in nodes
        )
    )
    canonical_edges = sorted(
        (
            json.dumps(
                [
                    _canonical_identifier(u),
                    _canonical_identifier(v),
                    _canonical_identifier(key),
                ],
                separators=(",", ":"),
                ensure_ascii=True,
            )
            for u, v, key in edges
        )
    )
    payload = json.dumps(
        {"nodes": canonical_nodes, "edges": canonical_edges},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()
