# Two-stage retrieval

A first-stage retriever maximizes candidate recall. A second-stage reranker spends greater compute
on a bounded set to improve top-rank precision. Evaluate candidate recall, top-rank quality, and
latency separately so a ranking gain is not confused with a retrieval gain.
