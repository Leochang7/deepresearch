# Data Engineering for LLM Training

## Data Quality Fundamentals

High-quality training data is critical for building capable large language models. Data engineering for LLM training involves collecting, filtering, deduplicating, and mixing data from diverse sources to maximize model capabilities.

## Deduplication

Data deduplication removes near-duplicate documents from training corpora to prevent memorization and improve diversity. Exact deduplication uses hash-based matching to remove identical documents. Fuzzy deduplication based on MinHash or SimHash detects documents that are substantially similar even if not identical. Studies show that deduplication can reduce training data by 20-50% while improving model performance.

## Quality Filtering

Quality filtering uses heuristic rules and trained classifiers to remove low-quality content. Common heuristics include minimum document length, language detection, perplexity filtering (removing text that is too random or too repetitive), and removal of boilerplate content. Classifier-based filtering trains models to distinguish high-quality text (e.g., Wikipedia) from low-quality web scrapes.

## Data Mixing

Data mixing ratios between sources like web text, books, code, and academic papers significantly affect model capabilities. The Dolma dataset and Llama training recipes carefully balance these sources. Over-representing code improves reasoning abilities, while diverse web text improves language understanding.
