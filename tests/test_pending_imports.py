from app.pending_imports import PendingImports


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_take_returns_the_file_once():
    store = PendingImports()
    token = store.put("apps.csv", b"data")
    assert store.take(token) == ("apps.csv", b"data")
    assert store.take(token) is None  # one-time use


def test_unknown_and_blank_tokens_return_nothing():
    store = PendingImports()
    assert store.take("nope") is None
    assert store.take("") is None


def test_tokens_are_long_and_unique():
    store = PendingImports()
    tokens = {store.put("a.csv", b"x") for _ in range(5)}
    assert len(tokens) == 5
    assert all(len(token) >= 24 for token in tokens)


def test_entries_expire():
    clock = FakeClock()
    store = PendingImports(ttl_seconds=60, clock=clock)
    token = store.put("a.csv", b"x")
    clock.now = 59
    assert store.take(store.put("b.csv", b"y")) == ("b.csv", b"y")
    clock.now = 61
    assert store.take(token) is None


def test_only_the_newest_entries_are_kept():
    store = PendingImports(max_items=2)
    first = store.put("1.csv", b"1")
    second = store.put("2.csv", b"2")
    third = store.put("3.csv", b"3")
    assert store.take(first) is None
    assert store.take(second) is not None
    assert store.take(third) is not None
