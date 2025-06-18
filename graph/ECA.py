import networkx as nx

def extract_cliques_from_explicit(graph, min_size=3):
    G = nx.Graph(graph)
    cliques = list(nx.find_cliques(G))
    return [set(c) for c in cliques if len(c) >= min_size]

def extract_components_from_implicit(graph, min_size=3):
    G = nx.Graph(graph)
    components = list(nx.connected_components(G))
    return [set(c) for c in components if len(c) >= min_size]

def jaccard(set1, set2):
    return len(set1 & set2) / len(set1 | set2)

# -----------------------
# Entity Cluster Algorithm 
# -----------------------

def entity_cluster_aggregation(temporal_graphs, strategy='explicit', gamma=0.8):
    merged_events = []
    prev_clusters = []

    for time, graph in sorted(temporal_graphs.items()):
        if strategy == 'explicit':
            clusters = extract_cliques_from_explicit(graph)
        else:
            clusters = extract_components_from_implicit(graph)

        new_clusters = []
        for c in clusters:
            merged = False
            for prev in prev_clusters:
                if strategy == 'explicit':
                    sim = jaccard(prev['entities'], c)
                    if sim >= gamma:
                        prev['entities'].update(c)
                        prev['end'] = time
                        merged = True
                        break
                else:  # implicit: share at least one entity
                    if prev['entities'] & c:
                        prev['entities'].update(c)
                        prev['end'] = time
                        merged = True
                        break
            if not merged:
                new_cluster = {
                    'entities': set(c),
                    'start': time,
                    'end': time
                }
                merged_events.append(new_cluster)
                new_clusters.append(new_cluster)
        prev_clusters = new_clusters  # only try to merge forward
    return merged_events
