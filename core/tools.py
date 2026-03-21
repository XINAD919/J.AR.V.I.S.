from datetime import datetime


def get_current_datetime() -> str:
    return datetime.now().strftime("%A, %d de %B de %Y, %H:%M:%S")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Obtiene la fecha y hora actual del sistema.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }
]

_REGISTRY = {
    "get_current_datetime": get_current_datetime,
}


def dispatch(name: str, args: dict) -> str:
    fn = _REGISTRY.get(name)
    if fn is None:
        return f"Tool '{name}' not found."
    return fn(**args)
