import json
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
import matplotlib.pyplot as plt


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def embedding(a: str) -> np.ndarray:
    sbert_model = SentenceTransformer('bert-base-nli-mean-tokens')
    return sbert_model.encode(a)


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
        doc_dict["doc_embedding"].append(sbert_model.encode(graph[doc]["first_paragraph"]))

        for t in ["linked_pages", "what_links_here"]:
            # for each of the subdocuments
            for subdoc in graph[doc][t]:
                subdoc_dict["doc"].append(graph[doc]["title"])
                subdoc_dict["subdoc"].append(subdoc)
                # find the embedding of those documents
                subdoc_dict["subdoc_embedding"].append(sbert_model.encode(subdoc["first_paragraph"]))

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
    plt.show()

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
