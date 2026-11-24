# E002b Original-Repository Merge Note

The historical complete repository is not present in the current execution environment, so a byte-for-byte merge into the original files could not be performed here.

The integrated `packages.search.retrieval.e001_adapter` wraps the original frozen `packages.search.retrieval.bm25.BM25Retriever`. It indexes E002b's document-text mappings through the `Email` model and translates normalized term queries and search hits without replacing E001 scoring. The included `simple_bm25.py` remains a standalone test double, not a runtime fallback.

Do not report a full historical-repository merge until this package is copied into the original repository and its entire pre-existing test suite passes.
