# Text Embeddings / 文本嵌入

## Overview

Text embeddings are dense vector representations of text that capture semantic meaning in a continuous vector space. Unlike traditional bag-of-words (BOW) or TF-IDF representations, which encode text as sparse vectors based on word frequency, text embeddings encode text into fixed-dimensional vectors that preserve semantic relationships between words and sentences.

## 概述

文本嵌入是文本的密集向量表示，能够在连续向量空间中捕获语义含义。与传统的词袋模型（BOW）或 TF-IDF 表示（基于词频将文本编码为稀疏向量）不同，文本嵌入将文本编码为固定维度的向量，保留了词语和句子之间的语义关系。

## Dense Embeddings vs Sparse Representations / 密集嵌入与稀疏表示

Traditional sparse representations like TF-IDF and bag-of-words models count word frequencies but lose word order and semantic nuance. Text embeddings capture semantic meaning by mapping text into dense, continuous vector spaces where semantically similar texts are positioned close together. Transformer-based models such as BERT, Sentence-BERT, and OpenAI's text-embedding-ada-002 produce high-quality dense embeddings that understand context, synonyms, and even cross-lingual similarity.

传统的稀疏表示如 TF-IDF 和词袋模型计算词频，但会丢失词序和语义细节。文本嵌入通过将文本映射到密集的连续向量空间来捕获语义含义，语义相似的文本在空间中位置相近。基于 Transformer 的模型（如 BERT、Sentence-BERT 和 OpenAI 的 text-embedding-ada-002）能够生成高质量的密集嵌入，理解上下文、同义词甚至跨语言相似性。

## Applications / 应用场景

Dense embeddings encode text into fixed-dimensional vectors, enabling efficient similarity search, clustering, and classification tasks. In RAG systems, embeddings are used to index documents and retrieve relevant passages by computing cosine similarity between the query embedding and document embeddings. The semantic richness of dense vectors makes them far superior to keyword-based approaches for capturing the intent behind natural language queries.

密集嵌入将文本编码为固定维度的向量，支持高效的相似度搜索、聚类和分类任务。在 RAG 系统中，嵌入用于索引文档，并通过计算查询嵌入和文档嵌入之间的余弦相似度来检索相关段落。密集向量的语义丰富性使其在捕获自然语言查询背后的意图方面远优于基于关键词的方法。
