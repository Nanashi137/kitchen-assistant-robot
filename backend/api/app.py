import os
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

from api.routers import auth, conversations, messages
from behavior_tree.build_tree import build_tree
from clients import MilvusHybridEntityStore, get_chat_model
from nodes import Blackboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LLM, vector DB, blackboard, and behavior tree; save tree image to artifacts/."""
    import py_trees.display
    from clients import DenseEmbedder, SparseEmbedder

    llm = get_chat_model()
    milvus_url = os.getenv("MILVUS_URL", "http://127.0.0.1:1013")
    text_embedding_url = os.getenv("TEXT_EMBEDDING_URL", "http://localhost:1012")
    text_embedding_dim = int(os.getenv("TEXT_EMBEDDING_DIM", "1024"))
    collection_name = os.getenv("COLLECTION_NAME", "entity")
    bm25_path = os.getenv("BM25_JSON_PATH", "../data/embedder/sparse.json")

    dense_embedder = DenseEmbedder(url=text_embedding_url)
    sparse_embedder = SparseEmbedder().load(bm25_path)
    vecdb = MilvusHybridEntityStore(
        uri=milvus_url,
        collection_name=collection_name,
        dense_dim=text_embedding_dim,
        dense_embedder=dense_embedder,
        sparse_embedder=sparse_embedder,
    )
    vecdb.ensure_collection()

    bb = Blackboard(name="api_bb")
    tree = build_tree(bb=bb, llm=llm, vecdb=vecdb)

    app.state.llm = llm
    app.state.vecdb = vecdb
    app.state.bb = bb
    app.state.tree = tree

    # Save tree to artifacts/
    artifacts_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "artifacts"
    )
    os.makedirs(artifacts_dir, exist_ok=True)
    dot_source = str(py_trees.display.dot_tree(tree.root))
    dot_path = os.path.join(artifacts_dir, "behavior_tree.dot")
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(dot_source)
    try:
        import graphviz

        graphviz.Source(dot_source).render(
            directory=artifacts_dir,
            filename="behavior_tree",
            format="png",
            cleanup=True,
        )
    except Exception:
        pass  # graphviz/dot binary may not be installed or available

    yield
    # Shutdown: nothing to tear down


app = FastAPI(title="Kitchen Assistant API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
