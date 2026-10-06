# LLM + Embedder Providers

## LLM Providers

All implement `LLMBase`. All support sync + async, tool calling, and automatic rate limiting.
Since v1.22 `neo4j_graphrag.llm` and `neo4j_graphrag.embeddings` resolve provider classes lazily — importing either no longer loads every provider SDK; public imports unchanged.

| Class | Extra | Notes |
|---|---|---|
| `OpenAILLM` | `openai` | Structured output; tool calling |
| `AzureOpenAILLM` | `openai` | Azure-hosted OpenAI |
| `AnthropicLLM` | `anthropic` | Structured output + tool calling (v1.19; needs Claude 4.5+) |
| `GeminiLLM` | `google` | Google GenAI SDK; added v1.17 (replaces deprecated-to-be `VertexAILLM`) |
| `VertexAILLM` | `google` | Structured output; tool calling; default model now `gemini-2.5-flash` (v1.19) |
| `MistralAILLM` | `mistralai` | Tool calling; requires `mistralai>=2.7.1` (v1.19, breaking) |
| `CohereLLM` | `cohere` | Constructible again since v1.19 |
| `OllamaLLM` | `ollama` | Local; tool calling |
| `BedrockLLM` | `bedrock` | Boto3 Converse API; default model now `us.anthropic.claude-haiku-4-5-...` (v1.19) |

```python
from neo4j_graphrag.llm import (
    OpenAILLM, AzureOpenAILLM, AnthropicLLM, GeminiLLM, VertexAILLM,
    MistralAILLM, CohereLLM, OllamaLLM, BedrockLLM,
    BaseOpenAILLM, BaseAnthropicLLM, BaseGeminiLLM,  # subclass to reach custom endpoints (v1.19)
)

llm = OpenAILLM(model_name="gpt-4.1", model_params={"temperature": 0})
llm = AnthropicLLM(model_name="claude-sonnet-4-5")
llm = GeminiLLM(model_name="gemini-2.5-flash")
llm = VertexAILLM(model_name="gemini-2.5-flash")
llm = OllamaLLM(model_name="llama3")           # no API key needed
llm = BedrockLLM(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")

# Custom / OpenAI-compatible endpoint (v1.19): explicit base_url on Anthropic, OpenAI, Azure, Gemini
llm = OpenAILLM(model_name="...", base_url="https://my-gateway.example.com/v1")
# Note: an http_client with its own base_url is ignored by the SDKs — pass base_url instead (warns)

# Token usage tracking (v1.15.0+)
response = llm.invoke("Hello")
# response.usage → LLMUsage(request_tokens=N, response_tokens=M, total_tokens=T)

# Graceful resource cleanup (v1.16.0+)
llm.close()         # sync
await llm.aclose()  # async
```

---

## Embedder Providers

All include automatic rate limiting with tenacity exponential backoff.

| Class | Extra | Dims |
|---|---|---|
| `OpenAIEmbeddings` | `openai` | 3072 / 1536 |
| `AzureOpenAIEmbeddings` | `openai` | varies |
| `GeminiEmbedder` | `google` | added v1.17 (replaces deprecated-to-be `VertexAIEmbeddings`) |
| `VertexAIEmbeddings` | `google` | 768 |
| `MistralAIEmbeddings` | `mistralai` | 1024 |
| `CohereEmbeddings` | `cohere` | 1024 |
| `OllamaEmbeddings` | `ollama` | varies |
| `SentenceTransformerEmbeddings` | `sentence-transformers` | 384+ |
| `BedrockEmbeddings` | `bedrock` | varies; added v1.15.0 |

```python
from neo4j_graphrag.embeddings import (
    OpenAIEmbeddings, VertexAIEmbeddings, GeminiEmbedder, CohereEmbeddings,
    OllamaEmbeddings, SentenceTransformerEmbeddings, BedrockEmbeddings,
)

# Cohere embeddings are asymmetric (v1.19): give the retrieval side its own instance
indexer_embedder = CohereEmbeddings(input_type="search_document")  # default, for TextChunkEmbedder
query_embedder = CohereEmbeddings(input_type="search_query")       # for the retriever

embedder = OpenAIEmbeddings(model="text-embedding-3-large")   # 3072 dims
embedder = OpenAIEmbeddings(model="text-embedding-3-small")   # 1536 dims
embedder = SentenceTransformerEmbeddings(model="all-MiniLM-L6-v2")  # 384 dims, local
embedder = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
```
