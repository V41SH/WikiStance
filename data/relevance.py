import json
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
import matplotlib.pyplot
import time
import pickle, atexit
from pathlib import Path
from collections.abc import Sequence                       # for type hint
import numpy as np

_CACHE_F = Path("embeddings.pkl")
try:
    _EMB_CACHE: dict[str, np.ndarray] = pickle.load(_CACHE_F.open("rb"))
except FileNotFoundError:
    _EMB_CACHE = {}

def _flush_cache() -> None:
    with _CACHE_F.open("wb") as fp:
        pickle.dump(_EMB_CACHE, fp, protocol=pickle.HIGHEST_PROTOCOL)

atexit.register(_flush_cache)



t1 = time.time()
MODEL = SentenceTransformer(
    'bert-base-nli-mean-tokens',
    device="cuda:0")
print(f"Loaded BERT model in {time.time() - t1} seconds")


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def embed_batch(
    titles: Sequence[str],
    texts: Sequence[str],
    batch_size: int = 24,
) -> np.ndarray:
    assert len(titles) == len(texts), "titles and texts must align"

    # work out which titles we have not embedded yet
    missing_idx = [i for i, t in enumerate(titles) if t not in _EMB_CACHE]

    if missing_idx:
        to_encode = [texts[i] for i in missing_idx]
        new_vecs = MODEL.encode(
            to_encode,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        for i, vec in zip(missing_idx, new_vecs):
            _EMB_CACHE[titles[i]] = vec

    return np.stack([_EMB_CACHE[t] for t in titles])




def main():
    # read the JSON file
    with open("wikipedia_final_data.json", "r") as f:
        graph = json.load(f)

    doc_dict = {"doc":[], "doc_embedding":[]}
    subdoc_dict = {"doc": [], "subdoc":[], "subdoc_embedding":[]}

    sbert_model = SentenceTransformer('bert-base-nli-mean-tokens')

    # iterate over each of the main documents
    for doc in graph:
        # calculate the embedding of the main documents
        doc_dict["doc"].append(graph[doc]["title"])
        doc_dict["doc_embedding"].append(
            embed_batch([graph[doc]["first_paragraph"]])[0]
        )
        subtexts, subhandles = [], []
        for t in ["linked_pages", "what_links_here"]:
            for subdoc in graph[doc][t]:
                subhandles.append(subdoc)  # keep handle for later
                subtexts.append(subdoc["first_paragraph"])

        for subdoc, emb in zip(subhandles, embed_batch(subtexts)):
            subdoc_dict["doc"].append(graph[doc]["title"])
            subdoc_dict["subdoc"].append(subdoc)
            subdoc_dict["subdoc_embedding"].append(emb)

    subdoc_df = pd.DataFrame(subdoc_dict)
    subdoc_df = subdoc_df.convert_dtypes()
    subdoc_df["subdoc_embeddings"] = subdoc_df["subdoc_embedding"].to_numpy()
    doc_df = pd.DataFrame(doc_dict)
    doc_df = doc_df.convert_dtypes()
    doc_df["doc_embeddings"] = doc_df["doc_embedding"].to_numpy()

    # compare
    doc_emb = dict(zip(doc_df["doc"], doc_df["doc_embeddings"]))

    # assign score to each of the documents
    subdoc_df["doc_similarity"] = subdoc_df.apply(
        lambda row: similarity(doc_emb[row["doc"]], row["subdoc_embeddings"]),
        axis=1
    )

    plt.hist(subdoc_df["doc_similarity"], bins=50)
    plt.xlabel("Cosine similarity")
    plt.ylabel("Frequency")
    plt.title("Histogram of document–subdocument similarities")
    # plt.show()

    threshold = 0.7

    mask = subdoc_df["doc_similarity"] >= threshold
    keep  = subdoc_df.loc[mask, ["doc", "subdoc"]]

    # allowed = keep.groupby("doc")["subdoc"]#.apply(set)
    allowed = keep.groupby("doc").apply(set)
    print(allowed.columns)

    # set threshold or rank all of the documents and filter them out or something
    for doc in graph:
        for t in ("linked_pages", "what_links_here"):
            graph[doc][t] = [s for s in graph[doc][t]
                                if s in allowed.get(graph[doc]["title"], set())]

    # write the filtered graph
    with open("wikipedia_filtered.json", "w") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
