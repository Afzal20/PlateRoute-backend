def bp_of(amount, bp):
    """Basis-point share of an integer amount, rounded half up (DR-005)."""
    return (amount * bp + 5000) // 10000
