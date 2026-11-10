def external_id_values(value):
    """Match a legacy BSON integer without conflating e.g. '001' and '1'."""
    text=str(value);values=[text]
    try:
        number=int(text)
        if str(number)==text and -(2**63)<=number<2**63:values.append(number)
    except (ValueError,TypeError):pass
    return values
