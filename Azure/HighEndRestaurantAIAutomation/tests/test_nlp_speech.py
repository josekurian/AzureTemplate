import importlib.util
import os
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

spec = importlib.util.spec_from_file_location('intent', os.path.join(root, 'app', 'nlp', 'intent.py'))
imap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imap)

spec2 = importlib.util.spec_from_file_location('trans', os.path.join(root, 'app', 'speech', 'transcribe.py'))
transmod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(transmod)

import asyncio

async def test_intent_and_transcribe():
    d = await imap.detect_intent('I want to make a reservation')
    assert d['intent'] == 'reservation'
    t = await transmod.transcribe('/tmp/file.wav')
    assert 'transcript' in t

if __name__ == '__main__':
    asyncio.run(test_intent_and_transcribe())
