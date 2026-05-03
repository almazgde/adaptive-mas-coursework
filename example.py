#!/usr/bin/env python3
"""Example script to demonstrate the adaptive MAS prototype."""

import asyncio
from adaptive_mas.dag import DAG, Node, Edge
from adaptive_mas.metrics import GraphMetrics
from adaptive_mas.topology import TopologySelector, TopologyType
from adaptive_mas.agents.mock_agents import PlannerAgent, ResearcherAgent


async def main():
    print("Adaptive MAS Prototype - Stage 1")

    # Create a simple DAG
    dag = DAG()
    dag.add_node(Node("plan", "Planning task"))
    dag.add_node(Node("research", "Research task"))
    dag.add_node(Node("critique", "Critique task"))
    dag.add_edge(Edge("plan", "research"))
    dag.add_edge(Edge("research", "critique"))

    print(f"DAG is acyclic: {dag.is_acyclic()}")
    print(f"Topological order: {dag.topological_sort()}")

    # Calculate metrics
    depth = GraphMetrics.graph_depth(dag)
    density = GraphMetrics.graph_density(dag)
    width = GraphMetrics.parallel_width(dag)
    print(f"Graph depth: {depth}")
    print(f"Graph density: {density:.2f}")
    print(f"Parallel width: {width}")

    # Select topology
    topology = TopologySelector.select_topology(dag, TopologyType.PARALLEL)
    print(f"Selected topology: {topology['type']}")
    print(f"Parallel groups: {topology['parallel_groups']}")

    # Run mock agents
    planner = PlannerAgent()
    researcher = ResearcherAgent()

    plan_result = await planner.execute({"task": "example"})
    research_result = await researcher.execute(plan_result)

    print(f"Planner result: {plan_result}")
    print(f"Researcher result: {research_result}")

    print("Prototype running successfully!")


if __name__ == "__main__":
    asyncio.run(main())