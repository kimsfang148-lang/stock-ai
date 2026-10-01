def scenarios(fair_value):
    if fair_value is None:
        return {}
    return {
        "bear": fair_value * 0.82,
        "base": fair_value,
        "bull": fair_value * 1.25,
    }
