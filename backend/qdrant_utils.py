# qdrant_utils.py
# ------------------------------------------------------------
# Junior (PL): Klient Qdrant przez URL + API KEY (REST).
#  - tworzę kolekcję jeśli nie istnieje
#  - upsert punktów
#  - wipe_source: kasuję wszystkie punkty danego źródła
#  - fetch_all: pobieram wszystkie punkty spełniające filtr (do exact-match po kluczu)
# ------------------------------------------------------------

import os
from typing import List, Optional, Union
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchValue, PointIdsList

COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")

class QdrantManager:
    def __init__(self, collection_name: Optional[str] = None):
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if not url or not api_key:
            raise RuntimeError("Brak QDRANT_URL lub QDRANT_API_KEY w środowisku (.env)")

        self.client = QdrantClient(url=url, api_key=api_key, prefer_grpc=False, timeout=10.0)
        self.collection_name = collection_name or COLLECTION
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def insert_vector(self, point_id: Union[str, int], vector: List[float], payload: dict):
        self.client.upsert(
            collection_name=self.collection_name,
            points=[{"id": point_id, "vector": vector, "payload": payload}],
        )

    def search_vectors(self, query_vector: List[float], limit: int = 10, query_filter=None):
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )

    def wipe_source(self, source: str) -> int:
        ids = []
        next_page = None
        flt = Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
        while True:
            recs, next_page = self.client.scroll(
                self.collection_name, limit=256, with_payload=False, scroll_filter=flt, offset=next_page
            )
            ids.extend([r.id for r in recs])
            if next_page is None:
                break
        if ids:
            self.client.delete(self.collection_name, points_selector=PointIdsList(points=ids))
        return len(ids)

    def fetch_all(self, query_filter: Filter, page_limit: int = 256):
        """Junior (PL): pobieram WSZYSTKIE rekordy spełniające filtr (payloady)."""
        items = []
        next_page = None
        while True:
            recs, next_page = self.client.scroll(
                self.collection_name, limit=page_limit, with_payload=True, scroll_filter=query_filter, offset=next_page
            )
            items.extend(recs)
            if next_page is None:
                break
        return items
