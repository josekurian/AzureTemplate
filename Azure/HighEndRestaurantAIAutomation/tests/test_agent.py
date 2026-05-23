import importlib.util
import os

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# load runtime and agent
spec = importlib.util.spec_from_file_location('runtime', os.path.join(root, 'app', 'agent_runtime', 'runtime.py'))
rmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmod)
AgentRuntime = getattr(rmod, 'AgentRuntime')

spec2 = importlib.util.spec_from_file_location('agent', os.path.join(root, 'app', 'agents', 'sample_agent.py'))
agentmod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(agentmod)
SampleAgent = getattr(agentmod, 'SampleAgent')

import asyncio

async def test_agent_tool_invocation():
    rt = AgentRuntime()
    async def fake_search(q):
        return {'hits': [{'id': '1', 'text': 'mock'}]}
    rt.register_tool('search', fake_search)
    agent = SampleAgent(rt)
    res = await agent.do_work('hello')
    assert 'hits' in res

if __name__ == '__main__':
    asyncio.run(test_agent_tool_invocation())
