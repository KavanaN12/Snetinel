from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from math import inf, isfinite
from typing import Hashable

NodeId = Hashable


@dataclass(frozen=True, slots=True)
class WeightedEdge:
    target: NodeId
    cost: float = 1.0


class DirectedGraphAnalysis:
    """Deterministic traversal and reachability algorithms for IAM attack graphs."""

    def __init__(self, adjacency: dict[NodeId, list[WeightedEdge]]) -> None:
        self.adjacency = adjacency

    def breadth_first_path(self, source: NodeId, target: NodeId) -> list[NodeId] | None:
        parents: dict[NodeId, NodeId | None] = {source: None}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            if current == target:
                return self._reconstruct_path(parents, target)
            for edge in self.adjacency.get(current, []):
                if edge.target not in parents:
                    parents[edge.target] = current
                    queue.append(edge.target)
        return None

    def depth_first_path(self, source: NodeId, target: NodeId) -> list[NodeId] | None:
        parents: dict[NodeId, NodeId | None] = {source: None}
        stack = [(source, iter(self.adjacency.get(source, [])))]
        while stack:
            current, neighbors = stack[-1]
            try:
                edge = next(neighbors)
            except StopIteration:
                stack.pop()
                continue
            if edge.target in parents:
                continue
            parents[edge.target] = current
            if edge.target == target:
                return self._reconstruct_path(parents, target)
            stack.append((edge.target, iter(self.adjacency.get(edge.target, []))))
        return None

    def dijkstra_path(self, source: NodeId, target: NodeId) -> tuple[list[NodeId], float] | None:
        distances: dict[NodeId, float] = {source: 0.0}
        parents: dict[NodeId, NodeId | None] = {source: None}
        pending: list[tuple[float, int, NodeId]] = [(0.0, 0, source)]
        sequence = 1
        while pending:
            distance, _, current = heapq.heappop(pending)
            if distance != distances.get(current):
                continue
            if current == target:
                return self._reconstruct_path(parents, target), distance
            for edge in self.adjacency.get(current, []):
                if not isfinite(edge.cost) or edge.cost < 0:
                    raise ValueError("Attack graph edge costs must be finite and non-negative")
                candidate = distance + edge.cost
                if candidate < distances.get(edge.target, inf):
                    distances[edge.target] = candidate
                    parents[edge.target] = current
                    heapq.heappush(pending, (candidate, sequence, edge.target))
                    sequence += 1
        return None

    def strongly_connected_components(self) -> list[set[NodeId]]:
        nodes = set(self.adjacency)
        nodes.update(edge.target for edges in self.adjacency.values() for edge in edges)
        visited: set[NodeId] = set()
        finish_order: list[NodeId] = []
        for start in nodes:
            if start in visited:
                continue
            visited.add(start)
            stack = [(start, iter(self.adjacency.get(start, [])))]
            while stack:
                node, neighbors = stack[-1]
                try:
                    edge = next(neighbors)
                except StopIteration:
                    finish_order.append(node)
                    stack.pop()
                    continue
                if edge.target not in visited:
                    visited.add(edge.target)
                    stack.append((edge.target, iter(self.adjacency.get(edge.target, []))))

        reverse: dict[NodeId, list[NodeId]] = {node: [] for node in nodes}
        for source, edges in self.adjacency.items():
            for edge in edges:
                reverse[edge.target].append(source)

        assigned: set[NodeId] = set()
        components: list[set[NodeId]] = []
        for start in reversed(finish_order):
            if start in assigned:
                continue
            component = set()
            stack = [start]
            assigned.add(start)
            while stack:
                node = stack.pop()
                component.add(node)
                for neighbor in reverse.get(node, []):
                    if neighbor not in assigned:
                        assigned.add(neighbor)
                        stack.append(neighbor)
            components.append(component)
        return components

    def blast_radius(self, source: NodeId) -> set[NodeId]:
        reached = {source}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for edge in self.adjacency.get(current, []):
                if edge.target not in reached:
                    reached.add(edge.target)
                    queue.append(edge.target)
        return reached

    def choke_points(self, sources: set[NodeId], targets: set[NodeId]) -> set[NodeId]:
        baseline_pairs = self._reachable_pairs(sources, targets)
        if not baseline_pairs:
            return set()
        candidates = set(self.adjacency)
        candidates.update(edge.target for edges in self.adjacency.values() for edge in edges)
        candidates.difference_update(sources)
        candidates.difference_update(targets)
        return {
            candidate
            for candidate in candidates
            if self._reachable_pairs(sources, targets, blocked=candidate) < baseline_pairs
        }

    def _reachable_pairs(
        self,
        sources: set[NodeId],
        targets: set[NodeId],
        blocked: NodeId | None = None,
    ) -> set[tuple[NodeId, NodeId]]:
        pairs = set()
        for source in sources:
            if source == blocked:
                continue
            reached = {source}
            queue = deque([source])
            while queue:
                current = queue.popleft()
                for edge in self.adjacency.get(current, []):
                    if edge.target == blocked or edge.target in reached:
                        continue
                    reached.add(edge.target)
                    queue.append(edge.target)
            pairs.update(
                (source, target)
                for target in targets
                if target != source and target in reached
            )
        return pairs

    @staticmethod
    def _reconstruct_path(
        parents: dict[NodeId, NodeId | None],
        target: NodeId,
    ) -> list[NodeId]:
        path = []
        current: NodeId | None = target
        while current is not None:
            path.append(current)
            current = parents[current]
        path.reverse()
        return path
