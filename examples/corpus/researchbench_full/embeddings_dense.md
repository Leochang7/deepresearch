# Dense Text Embeddings

Dense text embeddings represent a fundamental shift from traditional sparse representations like TF-IDF and bag-of-words models. Instead of encoding text as high-dimensional sparse vectors based on term frequency, dense embeddings compress semantic meaning into fixed-dimensional continuous vectors.

## Semantic Capture

The key advantage of dense embeddings is their ability to capture semantic meaning beyond simple keyword overlap. While TF-IDF treats documents as collections of independent terms, dense embeddings from transformer-based models like BERT understand synonymy, paraphrasing, and contextual meaning. This makes them dramatically better for semantic search where the query and document may share no exact keywords.

## Transformer-Based Models

Modern embedding models leverage transformer architectures to generate contextual representations. Models like sentence-transformers, E5, and text-embedding-ada produce fixed-dimensional vectors typically ranging from 384 to 3072 dimensions. These vectors encode rich semantic information and can be efficiently compared using cosine similarity or dot product operations.

## Performance

On semantic similarity benchmarks, transformer-based embeddings consistently outperform TF-IDF and BM25 for tasks requiring understanding of meaning rather than exact term matching. The gap is especially large for cross-lingual retrieval and paraphrase detection where surface-level features are insufficient.
