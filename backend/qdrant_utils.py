import os
from time import time
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, PayloadSchemaType
)

EMBED_DIM = 384

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "chatbot")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


class QdrantManager:
    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30.0,
        )
        self._ensure_collection()
        self._ensure_payload_indices()

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
            )

    def _ensure_payload_indices(self):
        index_specs = [
            ("q_norm", PayloadSchemaType.KEYWORD),
            ("source", PayloadSchemaType.KEYWORD),
            ("source_type", PayloadSchemaType.KEYWORD),
            ("file_type", PayloadSchemaType.KEYWORD),
            ("seq", PayloadSchemaType.INTEGER),
            ("ingested_at", PayloadSchemaType.INTEGER),
        ]
        for field_name, schema in index_specs:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=schema,
                )
            except Exception as e:
                msg = str(e).lower()
                if "already exists" in msg or "exists" in msg:
                    continue
                print(f"[QDRANT] Index warning '{field_name}': {e}")

    def insert_vector(self, point_id: str, vector, payload: dict):
        payload = dict(payload)
        payload.setdefault("ingested_at", int(time()))
        self.client.upsert(
            collection_name=self.collection_name,
            points=[{
                "id": point_id,
                "vector": vector,
                "payload": payload,
            }]
        )

    def search_exact_key(self, q_norm_value: str, source_filter: str | None = None, limit: int = 1):
        must = [FieldCondition(key="q_norm", match=MatchValue(value=q_norm_value))]
        if source_filter:
            must.append(FieldCondition(key="source", match=MatchValue(value=source_filter)))
        flt = Filter(must=must)
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=flt,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return points

    def semantic_search(self, query_vector, limit: int = 3):
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
        )
