# Retrieval-Augmented Generation (RAG)

RAG combines the strengths of retrieval-based and generation-based approaches to question answering.

## Core Architecture

1. **Document indexing**: Documents are chunked, embedded, and stored in a vector database.
2. **Query processing**: User queries are embedded and used to retrieve relevant document chunks.
3. **Context injection**: Retrieved chunks are inserted into the LLM prompt as context.
4. **Generation**: The LLM generates an answer grounded in the retrieved evidence.

## Advanced Patterns

- **Iterative RAG**: Multiple rounds of retrieval and generation to refine answers.
- **Self-RAG**: The model decides when to retrieve and evaluates its own outputs.
- **Graph RAG**: Using knowledge graphs to enhance retrieval with structured relationships.
- **Agentic RAG**: An agent orchestrates the retrieval process, deciding what to search for and when.

## Evaluation

Key metrics for RAG systems include:
- Faithfulness: Does the answer accurately reflect the retrieved context?
- Relevance: Are the retrieved documents relevant to the query?
- Completeness: Does the answer cover all relevant aspects?
