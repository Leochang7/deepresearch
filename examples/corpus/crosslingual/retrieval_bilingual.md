# Dense vs Sparse Retrieval / 密集检索与稀疏检索

## Overview

In information retrieval and vector search systems, two fundamental paradigms exist: dense retrieval and sparse retrieval. Understanding the distinction between these approaches is critical for building effective search and RAG pipelines.

## 密集检索 (Dense Retrieval)

Dense retrieval uses embeddings for semantic matching. Text passages are encoded into continuous vector representations using neural network models such as BERT or sentence transformers. At query time, the query is also encoded into a dense embedding, and similarity is computed using cosine distance or dot product in the embedding space. Dense retrieval excels at capturing semantic meaning even when the query and document use different vocabulary.

密集检索使用嵌入向量（embeddings）进行语义匹配。文本段落通过 BERT 或句子变换器等神经网络模型被编码为连续的向量表示。查询时，查询文本同样被编码为密集嵌入向量，然后在嵌入空间中通过余弦距离或点积计算相似度。密集检索擅长捕获语义含义，即使查询和文档使用不同的词汇也能匹配。

## 稀疏检索 (Sparse Retrieval)

Sparse retrieval like BM25 uses term frequency for keyword matching. BM25 is the most widely used sparse retrieval algorithm, scoring documents based on term frequency and inverse document frequency. Each document is represented as a sparse vector where only terms present in the document have non-zero values. BM25 excels at exact keyword matching, making it highly effective when users search for specific terms, proper nouns, or technical identifiers.

稀疏检索（如 BM25）使用词频进行关键词匹配。BM25 是最广泛使用的稀疏检索算法，它基于词频和逆文档频率对文档进行评分。每个文档被表示为一个稀疏向量，只有出现在文档中的词项才具有非零值。BM25 擅长精确的关键词匹配，当用户搜索特定术语、专有名词或技术标识符时非常有效。

## Comparison / 对比分析

Dense retrieval and sparse retrieval each have complementary strengths. Dense retrieval captures semantic similarity through embeddings, handling paraphrases and cross-lingual queries effectively. Sparse retrieval like BM25 provides reliable exact match performance with minimal computational overhead. Modern hybrid systems combine both approaches, using dense retrieval for semantic understanding and sparse retrieval for keyword precision, often fusing results with reciprocal rank fusion (RRF).

密集检索和稀疏检索各有互补的优势。密集检索通过嵌入向量捕获语义相似度，能够有效处理释义和跨语言查询。稀疏检索如 BM25 以最小的计算开销提供可靠的精确匹配性能。现代混合系统将两种方法结合使用，用密集检索实现语义理解，用稀疏检索保证关键词精度，通常通过倒数排名融合（RRF）来合并结果。
