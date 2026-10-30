import pytest

from src.modules.attack_path.graph_algorithms import DirectedGraphAnalysis, WeightedEdge


def test_search_algorithms_return_directed_paths_and_weighted_effort() -> None:
    graph = DirectedGraphAnalysis(
        {
            "user": [WeightedEdge("role", 3), WeightedEdge("bucket", 8)],
            "role": [WeightedEdge("bucket", 1)],
            "bucket": [],
        }
    )

    assert graph.breadth_first_path("user", "bucket") == ["user", "bucket"]
    assert graph.depth_first_path("user", "bucket") == ["user", "role", "bucket"]
    assert graph.dijkstra_path("user", "bucket") == (["user", "role", "bucket"], 4)
    assert graph.breadth_first_path("bucket", "user") is None


def test_scc_blast_radius_and_choke_points_are_computed_from_edges() -> None:
    graph = DirectedGraphAnalysis(
        {
            "user-a": [WeightedEdge("role"), WeightedEdge("role-b")],
            "role": [WeightedEdge("bucket")],
            "role-b": [WeightedEdge("bucket")],
            "bucket": [WeightedEdge("bucket-copy")],
            "bucket-copy": [],
            "island-a": [WeightedEdge("island-b")],
            "island-b": [WeightedEdge("island-a")],
        }
    )

    components = graph.strongly_connected_components()
    assert {"island-a", "island-b"} in components
    assert graph.blast_radius("user-a") == {
        "user-a",
        "role",
        "role-b",
        "bucket",
        "bucket-copy",
    }
    assert graph.choke_points({"user-a"}, {"bucket-copy"}) == {"bucket"}


def test_dijkstra_rejects_negative_effort_costs() -> None:
    graph = DirectedGraphAnalysis({"source": [WeightedEdge("target", -1)]})

    with pytest.raises(ValueError, match="non-negative"):
        graph.dijkstra_path("source", "target")
