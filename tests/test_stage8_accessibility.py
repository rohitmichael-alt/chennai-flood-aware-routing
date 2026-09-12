import numpy as np
import pytest

pytest.importorskip("scipy")

import networkx as nx

from chennai_routing.stage8_accessibility import _nearest_nodes


def test_stage8_snaps_in_projected_chennai_crs() -> None:
    graph = nx.MultiDiGraph()
    graph.add_node("west", x=80.20, y=13.08)
    graph.add_node("east", x=80.30, y=13.08)
    nodes, distances = _nearest_nodes(
        graph,
        np.asarray([80.201, 80.299]),
        np.asarray([13.08, 13.08]),
    )
    assert tuple(nodes) == ("west", "east")
    assert np.all(distances < 200)
