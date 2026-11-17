# E004: Second-Stage Reranking

## Question

Given an unchanged hybrid candidate set, does a stronger second-stage scorer improve top-10 quality
enough to justify its latency?

## Experimental isolation

The hybrid retriever must return the same candidate depth for control and treatment. Only the
reranker changes. Recall@50 checks candidate adequacy; NDCG@10 and MRR measure ordering.

## Initial implementation

The scaffold uses a transparent token-overlap reranker. This validates the interface and experiment
boundary. A public cross-encoder can later replace it as a new treatment.
