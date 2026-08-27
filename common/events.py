HANDLERS = {}


def on(kind):
    """Register a handler for an outbox event kind; apps call this at ready().
    Multiple handlers per kind are allowed and run in registration order."""

    def deco(fn):
        HANDLERS.setdefault(kind, []).append(fn)
        return fn

    return deco
