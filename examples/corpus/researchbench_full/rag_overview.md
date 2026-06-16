# Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation is an architecture that combines retrieval with generation for knowledge-intensive NLP tasks. Introduced by Lewis et al. at Facebook AI Research in 2020, RAG grounds language model outputs in external document collections.

## Architecture

The RAG pipeline consists of two main components: a retriever and a generator. The retriever performs similarity search over a document index using dense vector representations to find passages relevant to the query. The generator then takes these retrieved passages as context and produces a natural language answer.

## Hallucination Reduction

RAG reduces hallucination by anchoring responses in retrieved evidence rather than relying solely on the model's parametric knowledge. When the model generates an answer with RAG, it can point to specific retrieved passages as sources. This grounding in evidence makes RAG particularly valuable for factual question answering.

## Knowledge Updates

A key advantage of RAG is that knowledge can be updated by modifying the document index without retraining the underlying language model. This separates the knowledge store from the model parameters, enabling real-time knowledge updates at much lower cost than full model retraining.
