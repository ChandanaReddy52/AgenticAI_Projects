# Dataset v1 — Notion Help Documentation (RAC)

## Overview
This dataset contains a curated subset of public Notion Help / User Documentation,
treated as a stand-in for an internal company knowledge base.

The dataset is used to build and evaluate a Retrieval-Augmented Context (RAC)
semantic search system before adding generation or agent logic.

## Dataset Scope
- Total documents: 23
- Document type: Product / user manuals
- Categories:
  - Getting started
  - Settings
  - Troubleshooting

## Source
All documents are sourced from the official Notion Help Center:
https://www.notion.so/help

The content was manually extracted using reader-mode and lightly cleaned
to remove delivery-layer noise (e.g., video placeholders, navigation UI),
while preserving the original language and structure.

## Design Decisions
- Minimal cleaning to reflect real-world document ingestion
- Tables were flattened into paired text blocks to preserve semantic relationships
- No documents are added or removed after freezing (Dataset v1 is immutable)

## Intended Use
This dataset is intended for:
- Sentence embedding generation
- Vector indexing (FAISS)
- Semantic retrieval evaluation
- Relevance debugging

It is explicitly not optimized for presentation or keyword search.

## Limitations
- Content is limited to a single product domain (Notion)
- Some concepts overlap across documents by design
- Multimedia-only knowledge (videos) is not included
