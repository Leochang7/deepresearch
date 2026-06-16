# RAG: Retrieval-Augmented Generation / 检索增强生成

## Overview

Retrieval-Augmented Generation (RAG) is an architecture that combines retrieval and generation for question answering systems. RAG retrieves relevant documents before generating answers, grounding responses in factual sources rather than relying solely on the model's parametric knowledge.

## 概述

检索增强生成（RAG，Retrieval-Augmented Generation）是一种将检索与生成相结合的问答系统架构。RAG 在生成回答之前，先检索相关文档，将回答建立在真实来源的基础上，而不是仅仅依赖模型的参数知识。这种方法有效地减少了大语言模型的幻觉问题。

## Architecture / 架构设计

The RAG pipeline consists of two main components: a retriever and a generator. The retriever performs similarity search over a document index using dense vector representations to find passages relevant to the query. The generator then takes these retrieved passages as context and produces a natural language answer.

RAG 流水线由两个主要组件构成：检索器（retriever）和生成器（generator）。检索器使用密集向量表示在文档索引上进行相似度搜索，找到与查询相关的段落。然后，生成器将这些检索到的段落作为上下文，生成自然语言回答。

## Key Benefits / 核心优势

RAG has become a foundational technique for building knowledge-intensive applications. It combines retrieval and generation for question answering in a way that keeps responses factually grounded. RAG retrieves relevant documents before generating answers, which significantly improves accuracy and reduces hallucination compared to pure generation approaches.

RAG 已经成为构建知识密集型应用的基础技术。通过在生成答案之前检索相关文档，系统能够提供更准确、更有据可查的回答。与纯生成方法相比，RAG 在减少幻觉、提升事实准确性方面表现显著。
