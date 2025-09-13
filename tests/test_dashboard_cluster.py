import numpy as np
import umap
from sklearn.datasets import load_iris
from sklearn.metrics import pairwise_distances


def test_umap_clusters_iris():
    data = load_iris().data
    labels = load_iris().target
    reducer = umap.UMAP(n_neighbors=5, min_dist=0.1, random_state=42)
    embedding = reducer.fit_transform(data)
    assert embedding.shape == (150, 2)
    centroids = [embedding[labels == i].mean(axis=0) for i in range(3)]
    dists = pairwise_distances(centroids)
    assert (dists[np.triu_indices(3, k=1)] > 1.0).all()
