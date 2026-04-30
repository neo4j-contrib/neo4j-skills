# GenAI Plugin — Full Provider Configuration Reference

All `ai.text.*` functions and `ai.text.embedBatch` accept `configuration :: MAP` as last argument.

Provider strings are **lowercase and exact** — case-sensitive.

---

## OpenAI (`'openai'`)

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `token` | STRING | Yes | — | OpenAI API key |
| `model` | STRING | Yes | — | e.g. `'text-embedding-3-small'`, `'gpt-4o-mini'` |
| `maxBatchSize` | INTEGER | No | 8192 | Max tokens per batch request |
| `vendorOptions` | MAP | No | `{}` | Extra OpenAI params, e.g. `{ dimensions: 1024 }` for reduced embedding dims |
| `chatHistory` | LIST<ANY> | No | — | Completion/chat only. `[{ role: 'user', content: '...' }, ...]` |

### Embed example
```cypher
CYPHER 25
RETURN ai.text.embed('Hello', 'openai', {
  token: $openaiKey, model: 'text-embedding-3-small',
  vendorOptions: { dimensions: 1024 }
}) AS v
```

### Completion example
```cypher
CYPHER 25
RETURN ai.text.completion('Summarize: ' + $text, 'openai', {
  token: $openaiKey, model: 'gpt-4o-mini',
  vendorOptions: { instructions: 'Be concise.' }
}) AS summary
```

---

## Azure OpenAI (`'azure-openai'`)

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `token` | STRING | Yes | — | Azure OAuth2 bearer token |
| `resource` | STRING | Yes | — | Azure resource name (subdomain of openai.azure.com) |
| `model` | STRING | Yes | — | Deployment name in Azure portal |
| `maxBatchSize` | INTEGER | No | 8192 | Embed batch only |
| `vendorOptions` | MAP | No | `{}` | Extra Azure params |
| `chatHistory` | LIST<ANY> | No | — | Completion/chat only |

### Example
```cypher
CYPHER 25
RETURN ai.text.embed('Hello', 'azure-openai', {
  token: $azureToken,
  resource: 'my-azure-resource',
  model: 'text-embedding-3-small'
}) AS v
```

---

## Google VertexAI (`'vertexai'`)

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `model` | STRING | Yes | — | Full model resource name, e.g. `'gemini-embedding-001'` |
| `project` | STRING | Yes | — | Google Cloud project ID |
| `region` | STRING | Yes | — | e.g. `'us-central1'`, `'asia-northeast1'` |
| `token` | STRING | Yes* | — | Service account access token (*one of token/apiKey) |
| `apiKey` | STRING | Yes* | — | API key alternative to `token` |
| `publisher` | STRING | No | `'google'` | Model publisher |
| `vendorOptions` | MAP | No | `{}` | e.g. `{ outputDimensionality: 1024 }` |
| `chatHistory` | LIST<ANY> | No | — | Format: `[{ role: 'user', parts: [{ text: '...' }] }]` |

**Note**: `ai.text.chat()` NOT supported on VertexAI — use openai/azure-openai for chat.

### Example
```cypher
CYPHER 25
RETURN ai.text.embed('Hello', 'vertexai', {
  token: $vertexToken,
  model: 'gemini-embedding-001',
  project: 'my-gcp-project',
  region: 'us-central1',
  vendorOptions: { outputDimensionality: 1024 }
}) AS v
```

---

## Amazon Bedrock — Embeddings (`'bedrock-titan'`)

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `model` | STRING | Yes | — | e.g. `'amazon.titan-embed-text-v1'` |
| `region` | STRING | Yes | — | AWS region e.g. `'eu-west-2'` |
| `accessKeyId` | STRING | Yes | — | AWS access key ID |
| `secretAccessKey` | STRING | Yes | — | AWS secret access key |
| `vendorOptions` | MAP | No | `{}` | e.g. `{ dimensions: 1024 }` |

### Example
```cypher
CYPHER 25
RETURN ai.text.embed('Hello', 'bedrock-titan', {
  accessKeyId: $awsKeyId,
  secretAccessKey: $awsSecret,
  model: 'amazon.titan-embed-text-v1',
  region: 'eu-west-2'
}) AS v
```

---

## Amazon Bedrock — Completions (`'bedrock-nova'`)

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `model` | STRING | Yes | — | Model ID or ARN, e.g. `'us.amazon.nova-micro-v1:0'` |
| `region` | STRING | Yes | — | AWS region |
| `accessKeyId` | STRING | Yes | — | AWS access key ID |
| `secretAccessKey` | STRING | Yes | — | AWS secret access key |
| `vendorOptions` | MAP | No | `{}` | Bedrock-specific options |
| `chatHistory` | LIST<ANY> | No | — | Conversation history |

**Note**: `ai.text.chat()` NOT supported on Bedrock — use openai/azure-openai for chat.

---

## Provider Discovery — Runtime Check

List all providers configured and available:
```cypher
// Embedding providers
CYPHER 25
CALL ai.text.embed.providers()
YIELD name, requiredConfigType, optionalConfigType, defaultConfig
RETURN name, requiredConfigType;

// Completion providers
CYPHER 25
CALL ai.text.completion.providers()
YIELD name, requiredConfigType, optionalConfigType
RETURN name;

// Chat providers
CYPHER 25
CALL ai.text.chat.providers()
YIELD name
RETURN name;

// Token count providers
CYPHER 25
CALL ai.text.tokenCount.providers()
YIELD name
RETURN name;
```

---

## Model Reference

| Provider | Embedding models | Completion models |
|---|---|---|
| OpenAI | `text-embedding-3-small` (1536d), `text-embedding-3-large` (3072d), `text-embedding-ada-002` (1536d, legacy) | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| Azure | Same as OpenAI (deployment-name based) | Same as OpenAI |
| VertexAI | `gemini-embedding-001` (3072d), `text-embedding-004` (768d) | `gemini-2.0-flash`, `gemini-1.5-pro` |
| Bedrock | `amazon.titan-embed-text-v1` (1536d), `amazon.titan-embed-text-v2:0` (1024d) | `us.amazon.nova-micro-v1:0`, `us.amazon.nova-lite-v1:0`, `us.amazon.nova-pro-v1:0` |

`vector.dimensions` in vector index MUST match model output dimensions exactly.
