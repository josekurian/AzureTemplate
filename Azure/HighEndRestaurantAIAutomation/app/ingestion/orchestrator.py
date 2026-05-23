class IngestionOrchestrator:
    def __init__(self, embedder=None, indexer=None):
        self.embedder = embedder
        self.indexer = indexer

    async def ingest(self, docs: list):
        # simple flow: embed -> index
        embeddings = await self.embedder.embed([d.get('text','') for d in docs])
        await self.indexer.index_documents(docs)
        return {'ingested': len(docs)}
