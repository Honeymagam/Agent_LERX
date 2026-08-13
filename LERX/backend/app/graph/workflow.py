"""LangGraph definition for the run lifecycle.

Side effects remain in the orchestrator so every file write and command execution is
captured transactionally, while LangGraph owns the explicit state transition model.
"""
from typing import TypedDict
from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict, total=False):
    user_request: str
    repository_url: str
    repository_path: str
    repository_summary: dict
    relevant_files: list[str]
    plan: dict
    changes: list[dict]
    test_results: dict
    errors: list[str]
    security_findings: list[dict]
    review: dict
    iteration: int
    status: str
    pipeline: list[str]


def _stage(name: str):
    def visit(state: AgentState) -> AgentState:
        return {"pipeline": [*state.get("pipeline", []), name]}
    return visit


def build_workflow():
    graph = StateGraph(AgentState)
    stages = ["repository-analyzer", "retriever", "planner", "implementation", "tester", "security", "reviewer"]
    for stage in stages: graph.add_node(stage, _stage(stage))
    graph.add_edge(START, stages[0])
    for current, following in zip(stages, stages[1:]): graph.add_edge(current, following)
    graph.add_edge(stages[-1], END)
    return graph.compile()
