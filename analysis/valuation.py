def reference_fair_value(price, pe=None, pb=None):
    if not price:
        return None
    try:
        if pe and pe > 0:
            value = price * (20 / pe)
        elif pb and pb > 0:
            value = price * (2 / pb)
        else:
            value = price
        return max(price*0.5, min(price*1.8, value))
    except Exception:
        return price
