# Keyword and vector search

A search system needs a quick way to decide which stored messages might answer
a question. LocalLore represents every searchable message in two different
ways:

- as words in an **inverted index** for keyword search;
- as numbers in an **embedding vector** for semantic search.

The two representations solve different problems. One preserves exact words;
the other captures approximate meaning.

## What is an index?

An index is extra data created from the original messages to make retrieval
easier. It plays the same role as the index at the back of a book: instead of
reading every page, you look up a term and jump to likely pages.

Indexes cost storage and take work to update, but they make repeated searches
more useful or more efficient.

## The inverted index

A normal, or forward, view starts with a message and lists its words:

```text
message 1 → docker, binds, local, port
message 2 → sqlite, powers, local, search
```

An **inverted index** reverses that relationship. It starts with each word and
lists the messages containing it:

```text
docker → message 1
local  → message 1, message 2
search → message 2
sqlite → message 2
```

This is sometimes called a reverse index, but *inverted index* is the standard
term. A query for `sqlite search` can use these lists instead of inspecting
every stored message.

LocalLore delegates this job to SQLite FTS5. FTS5 tokenizes message text,
maintains the inverted index as rows change, and ranks matching messages with
BM25. Keyword search is especially useful for exact identifiers, file names,
error messages, and uncommon technical terms.

## Embedding vectors

Keyword search misses relationships between different words. A message about
“restricting network access,” for example, may be relevant to a query about
“security boundaries” even if the phrases do not overlap.

An embedding model converts a piece of text into a fixed-length list of
numbers called a **vector**. LocalLore's default model produces 384 numbers per
message. Texts with related meanings tend to produce vectors that point in
similar directions.

At search time LocalLore:

1. creates a vector for the query;
2. compares it with the stored message vectors;
3. assigns higher similarity to vectors pointing in similar directions; and
4. sorts the messages from most to least similar.

LocalLore normalizes the vectors, so their dot product is equivalent to cosine
similarity. The magnitude of a vector does not affect the result; its direction
does.

## Vector search is not an inverted index

The inverted index maps discrete terms to messages. Vector search compares
dense numerical representations. They are separate retrieval paths:

| Property | Inverted-index search | Vector search |
| --- | --- | --- |
| Represents | Exact tokens | Approximate meaning |
| Strong at | Names, paths, errors, quoted terms | Paraphrases and related concepts |
| LocalLore implementation | SQLite FTS5 and BM25 | Local embeddings and NumPy dot products |
| Typical failure | Different wording | Semantically similar but wrong result |

LocalLore stores vectors in SQLite, but it does not build a specialized
approximate-nearest-neighbor vector index. It loads the vectors that match the
requested filters, compares all of them with NumPy, and sorts the scores. This
exact scan keeps the implementation small and understandable, but its work
grows with the number of stored messages.

## Why use both?

Neither method is consistently better. If a query contains a precise error
code, keyword search should dominate. If it paraphrases an earlier discussion,
vector search may find the connection. LocalLore runs both and combines their
ranked result lists.

Continue with [Embeddings and hybrid search](hybrid-search.md) to see how
LocalLore merges those rankings, or [RAG and LocalLore](rag.md) to see where
retrieval fits into the complete question-answering flow.
