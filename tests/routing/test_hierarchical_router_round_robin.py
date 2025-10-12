from src.routing.hierarchical_router import HierarchicalRouter
from src.entities import Agent, Task


def make_backend_agent(role: str):
    return Agent(role=role, capabilities=["api", "redis", "backend"], tier=3, specialization="backend")


def test_round_robin_selection_for_exact_matches():
    router = HierarchicalRouter()

    agents = [
        make_backend_agent("backend-specialist-A"),
        make_backend_agent("backend-specialist-B"),
    ]

    task = Task(description="Implement backend API with redis caching and database schema")

    # First routing → A, second → B, third → A
    a1 = router.route(task, agents)
    a2 = router.route(task, agents)
    a3 = router.route(task, agents)

    assert a1.role == "backend-specialist-A"
    assert a2.role == "backend-specialist-B"
    assert a3.role == "backend-specialist-A"

