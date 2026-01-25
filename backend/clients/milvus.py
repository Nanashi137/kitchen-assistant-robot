import asyncio
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from pymilvus import (AnnSearchRequest, CollectionSchema, DataType,
                      FieldSchema, MilvusClient, WeightedRanker)

SparseVec = Dict[int, float]


def _normalize_weights(w_dense: float, w_sparse: float) -> Tuple[float, float]:
    w_dense = float(w_dense)
    w_sparse = float(w_sparse)
    s = w_dense + w_sparse
    if s <= 0:
        return 0.5, 0.5
    return w_dense / s, w_sparse / s


def _ensure_sparse_keys_int(v: SparseVec) -> SparseVec:
    out: SparseVec = {}
    for k, val in (v or {}).items():
        try:
            ik = int(k)
        except Exception:
            continue
        fv = float(val)
        if fv != 0.0 and not math.isnan(fv) and math.isfinite(fv):
            out[ik] = fv
    return out


def _hit_get(hit: Any, key: str, default=None):
    if hasattr(hit, key):
        return getattr(hit, key)
    if isinstance(hit, dict):
        return hit.get(key, default)
    return default


def _hit_entity_field(hit: Any, field: str) -> Optional[Any]:
    ent = _hit_get(hit, "entity", None)
    if isinstance(ent, dict):
        return ent.get(field)
    return _hit_get(hit, field, None)


@dataclass
class SearchResultRow:
    id: Union[int, str]
    entity: str
    score: float


class MilvusHybridEntityStore:
    def __init__(
        self,
        *,
        uri: str,
        collection_name: str,
        dense_dim: int,
        dense_embedder,
        sparse_embedder,
        token: Optional[str] = None,
        db_name: Optional[str] = None,
    ):
        self.collection_name = collection_name
        self.dense_dim = int(dense_dim)
        self.dense = dense_embedder
        self.sparse_embedder = sparse_embedder

        kwargs = {}
        if token:
            kwargs["token"] = token
        if db_name:
            kwargs["db_name"] = db_name

        self.client = MilvusClient(uri=uri, **kwargs)

    def ensure_collection(
        self,
        *,
        entity_max_length: int = 256,
        hnsw_M: int = 8,
        hnsw_efConstruction: int = 64,
        sparse_drop_ratio_build: float = 0.2,
    ) -> None:
        if self.client.has_collection(self.collection_name):
            self.client.load_collection(self.collection_name)
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(
                name="entity", dtype=DataType.VARCHAR, max_length=entity_max_length
            ),
            FieldSchema(
                name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.dense_dim
            ),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
        ]
        schema = CollectionSchema(fields=fields, enable_dynamic_field=False)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_name="dense_hnsw",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": hnsw_M, "efConstruction": hnsw_efConstruction},
        )
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_inverted",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
            params={"drop_ratio_build": float(sparse_drop_ratio_build)},
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(self.collection_name)

    def insert_entities(
        self, entities: Sequence[str], *, batch_size: int = 256
    ) -> None:
        ents = [e for e in (entities or []) if isinstance(e, str) and e.strip()]
        if not ents:
            return

        for i in range(0, len(ents), batch_size):
            batch = ents[i : i + batch_size]

            dense_vecs = self.dense.embed(list(batch))
            sparse_vecs = self.sparse_embedder.embed(list(batch))

            if not isinstance(sparse_vecs, list):
                sparse_vecs = [sparse_vecs] * len(batch)

            rows: List[Dict[str, Any]] = []
            for ent, dv, sv in zip(batch, dense_vecs, sparse_vecs):
                sv = _ensure_sparse_keys_int(sv or {})
                rows.append(
                    {
                        "entity": ent,
                        "dense_vector": dv,
                        "sparse_vector": sv,
                    }
                )

            self.client.insert(collection_name=self.collection_name, data=rows)

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        rerank_k: Optional[int] = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        min_score: Optional[float] = None,
        dense_search_params: Optional[Dict[str, Any]] = None,
        sparse_search_params: Optional[Dict[str, Any]] = None,
        output_fields: Optional[List[str]] = None,
    ) -> List[SearchResultRow]:
        if not isinstance(query, str) or not query.strip():
            return []

        top_k = int(top_k)
        rerank_k = int(rerank_k) if rerank_k is not None else max(top_k * 4, top_k)

        w_dense, w_sparse = _normalize_weights(dense_weight, sparse_weight)

        dense_q = (self.dense.embed(query))[0]  # List[float]
        sparse_q = _ensure_sparse_keys_int(self.sparse_embedder.embed(query) or {})

        dense_params = dense_search_params or {
            "metric_type": "COSINE",
            "params": {"ef": 64},
        }
        sparse_params = sparse_search_params or {
            "metric_type": "IP",
            "params": {"drop_ratio_search": 0.0},
        }

        out_fields = output_fields or ["entity"]

        reqs: List[AnnSearchRequest] = []
        weights: List[float] = []

        if w_dense > 0:
            reqs.append(
                AnnSearchRequest(
                    data=[dense_q],
                    anns_field="dense_vector",
                    param=dense_params,
                    limit=rerank_k,
                )
            )
            weights.append(w_dense)

        if w_sparse > 0 and sparse_q:
            reqs.append(
                AnnSearchRequest(
                    data=[sparse_q],
                    anns_field="sparse_vector",
                    param=sparse_params,
                    limit=rerank_k,
                )
            )
            weights.append(w_sparse)

        if not reqs:
            return []

        if len(reqs) == 1:
            r0 = reqs[0]
            res = self.client.search(
                collection_name=self.collection_name,
                data=r0.data,
                anns_field=r0.anns_field,
                limit=top_k,
                search_params=r0.param,
                output_fields=out_fields,
            )
        else:
            ranker = WeightedRanker(*weights)
            res = self.client.hybrid_search(
                collection_name=self.collection_name,
                reqs=reqs,
                ranker=ranker,
                limit=top_k,
                output_fields=out_fields,
            )

        hits = res[0] if isinstance(res, list) else res  # be tolerant
        out: List[SearchResultRow] = []

        for hit in hits:
            hid = _hit_get(hit, "id", None)
            score = float(_hit_get(hit, "distance", _hit_get(hit, "score", 0.0)))
            ent = _hit_entity_field(hit, "entity")
            if ent is None:
                # fallback if output_fields differs
                ent = str(_hit_entity_field(hit, out_fields[0]) or "")
            if min_score is not None and score < float(min_score):
                continue
            out.append(SearchResultRow(id=hid, entity=str(ent), score=score))

        return out
