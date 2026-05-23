from typing import Callable

class AgentRuntime:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name: str, func: Callable, allowed_roles: list | None = None):
        self.tools[name] = {"func": func, "roles": allowed_roles}

    async def call_tool(self, name: str, *args, **kwargs):
        entry = self.tools.get(name)
        if not entry:
            raise RuntimeError('Tool not registered')
        func = entry['func']
        res = func(*args, **kwargs)
        # support sync or async
        import inspect
        if inspect.isawaitable(res):
            return await res
        return res
