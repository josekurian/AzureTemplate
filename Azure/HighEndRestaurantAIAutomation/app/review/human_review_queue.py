class HumanReviewQueue:
    def __init__(self):
        self.queue = []

    async def enqueue(self, item: dict):
        self.queue.append(item)
        return {'queued': True, 'id': len(self.queue)}

    async def list(self):
        return list(self.queue)
