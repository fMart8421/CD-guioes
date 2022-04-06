from enum import Enum

class Serializer(Enum):
    """Possible message serializers."""

    JSON = 0
    XML = 1
    PICKLE = 2


class MiddlewareType(Enum):
    """Middleware Type."""

    CONSUMER = 1
    PRODUCER = 2