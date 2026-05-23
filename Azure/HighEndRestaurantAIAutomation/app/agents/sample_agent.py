class SampleAgent:
    def __init__(self, runtime):
        self.runtime = runtime

    async def do_work(self, query: str):
        # call a registered tool named 'search'
        res = await self.runtime.call_tool('search', query)
        return res
