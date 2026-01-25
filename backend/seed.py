import asyncio
import os

import dotenv
import pandas as pd

from clients import DenseEmbedder, MilvusHybridEntityStore, SparseEmbedder

dotenv.load_dotenv()

MILVUS_URL = os.getenv("MILVUS_URL", "milvus:19530")
TEXT_EMBEDDING_URL = os.getenv("TEXT_EMBEDDING_URL", "http://text-embedding:2022")
TEXT_EMBEDDING_DIM = int(os.getenv("TEXT_EMBEDDING_DIM", "1024"))

BM25_JSON_PATH = os.getenv("BM25_JSON_PATH", "../data/embedder/sparse.json")
DATA_PATH = os.getenv("DATA_PATH", "../data/ambik/AmbiK_data.csv")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "entity")


def build_corpus_from_environment_short(
    csv_path: str, col: str = "environment_short", delim: str = ","
) -> list[str]:
    df = pd.read_csv(csv_path, index_col=None)
    if col not in df.columns:
        raise ValueError(f"Missing column '{col}'. Available: {list(df.columns)}")

    entities = set()
    for row in df[col].dropna().astype(str).tolist():
        for e in row.split(delim):
            e = e.strip()
            if e:
                entities.add(e)

    entities = sorted(entities, key=lambda x: x.lower())

    print(f"Corpus size (unique entities): {len(entities)}")

    sparse = SparseEmbedder()
    sparse.fit(entities)

    os.makedirs(os.path.dirname(BM25_JSON_PATH) or ".", exist_ok=True)
    sparse.save(BM25_JSON_PATH)

    print(f"Saved BM25 sparse embedder to: {BM25_JSON_PATH}")


if __name__ == "__main__":
    build_corpus_from_environment_short(DATA_PATH)

    dense_embedder = DenseEmbedder(url=TEXT_EMBEDDING_URL)
    sparse_embedder = SparseEmbedder().load(BM25_JSON_PATH)

    store = MilvusHybridEntityStore(
        uri=MILVUS_URL,
        collection_name=COLLECTION_NAME,
        dense_dim=TEXT_EMBEDDING_DIM,
        dense_embedder=dense_embedder,
        sparse_embedder=sparse_embedder,
    )

    store.ensure_collection()

    # Load data
    df = pd.read_csv(DATA_PATH, index_col=None)
    entity_columns = df["environment_short"].tolist()

    # Extract unique entities
    entities = set()
    for entity_row in entity_columns:
        for entity in entity_row.split(","):
            entity = entity.strip()
            if entity:
                entities.add(entity)
    print(len(entities), "unique entities found.")
    try:
        store.insert_entities(entities, batch_size=32)
        print(
            f"Inserted {len(entities)} entities into Milvus collection {COLLECTION_NAME}."
        )
    except Exception as e:
        print(f"Error inserting entities: {e}")
