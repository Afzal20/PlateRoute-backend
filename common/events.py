HANDLERS = {}


def on(kind):
    """Register a handler for an outbox event kind; apps call this at ready()."""

    def deco(fn):
        HANDLERS[kind] = fn
        return fn

    return deco
