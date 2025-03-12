def serialize(obj):
    """Convert non-serializable objects to JSON-compatible formats.
    Args:
        obj: The object to serialize.
    Returns:
        A JSON-compatible representation of the object.
    Raises:
        TypeError: If the object cannot be serialized.
    """
    if isinstance(obj, set):
        return list(obj)  # Convert sets to lists
    if hasattr(obj, "__dict__"):
        return obj.__dict__  # Convert objects with attributes to dicts
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
