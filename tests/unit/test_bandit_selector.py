from src.routing.bandit import EpsilonGreedyBandit


def test_bandit_explores_and_exploits(monkeypatch):
    b = EpsilonGreedyBandit(variants=["a","b"], epsilon=0.0)
    # With no rewards and epsilon=0, ties resolved by counts; both 0 => choose first by max key order
    v1 = b.select()
    assert v1 in ("a","b")
    # Update rewards to prefer 'b'
    for _ in range(5):
        b.update("b", 1.0)
    for _ in range(2):
        b.update("a", 0.0)
    # Now it should exploit 'b' consistently when epsilon=0
    for _ in range(10):
        assert b.select() == "b"

