"""Engine-neutral types for exact shortest-path queries on metric snapshots."""

from __future__ import annotations

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
