# Property Encryption [6.3.0+, preview]

Client-side envelope encryption of property values. Server-version agnostic — ciphertext stored as byte-array property. Cross-driver interoperable (Java, Go, JS) when profiles match. Preview: API may change without deprecation cycle.

Source: [Property Encryption discussion #1471](https://github.com/neo4j/neo4j-javascript-driver/discussions/1471)

## Crypto parameters (fixed)

| Item | Value |
|---|---|
| Data key | AES-256 |
| Algorithm | AES-GCM (`AES/GCM/NoPadding`) |
| IV | 12 bytes |
| Auth tag | 16 bytes |
| AAD | optional; must match on decrypt |

## Components

| Component | Provided by | Role |
|---|---|---|
| `KeyEncapsulationService` | driver (`neo4j.localKeyEncapsulationService(masterKey)`, 32-byte `Uint8Array`) or user | `encapsulate(options)` / `decapsulate(encapsulation, metadata)` AES-256 data keys. Cloud KMS (AWS/Azure/GCP) → separate npm packages, not in driver |
| `EncapsulatedKeyRecordRepository` | **user** — no built-in | persist encapsulated keys; assign globally unique immutable ids; enforce alias uniqueness. Methods: `create(alias, encapsulation, metadata)`, `findById`, `findByAlias`, `setAliasById(id, alias)`, `deleteById` — all return Promises |
| `EnvelopeEncryptionProfile` | driver | named profile; name stored with each encrypted value — must match on every reading driver |

`EnvelopeEncryptionProfile` options: `name`, `encapsulationService`, `keyRepository` (required); `keyCacheTTL` ms (default 15 min), `keyCacheMaxSize` (default 100, `0` disables), `keyAliasIndexTTL` ms (default 15 s), `keyAliasIndexMaxSize` (default 100, `0` disables).

## Setup

```javascript
import neo4j from 'neo4j-driver'

const driver = neo4j.driver(process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD), {
    encryptionProfiles: [new neo4j.EnvelopeEncryptionProfile({
      name: 'customer-pii',                                              // unique per driver
      encapsulationService: neo4j.localKeyEncapsulationService(masterKey), // load from secret store, never hardcode
      keyRepository: keyRepo                                             // your EncapsulatedKeyRecordRepository
    })]
  })

// Create data key once — must exist before encrypting
const keyManager = driver.encryption.keyManager('customer-pii')  // undefined allowed when 1 profile
await keyManager.create('current')                                // alias; also findByAlias, findById, setAliasById, deleteAliasById
```

## Encrypt / store / decrypt

```javascript
const ssnEnc = await driver.encryption.encrypt({
  value: '078-05-1120',          // any Neo4j property type
  keyOptions: { alias: 'current' }, // plain string = key id
  encryptionProfile: 'customer-pii', // optional when 1 profile
  aad: 'customer-1'              // bind ciphertext to context; non-secret
})                               // → Int8Array, sent as byte array

await driver.executeQuery(
  'MERGE (c:Customer {id: $id}) SET c.ssnEnc = $enc',
  { id: 'customer-1', enc: ssnEnc },
  { database: 'neo4j' })

const { records } = await driver.executeQuery(
  'MATCH (c:Customer {id: $id}) RETURN c.ssnEnc AS enc',
  { id: 'customer-1' },
  { database: 'neo4j', routing: neo4j.routing.READ })
const ssn = await driver.encryption.decrypt({
  ciphertext: records[0].get('enc'),
  aad: 'customer-1'              // same AAD, else fails; or usePersistedAad: true (mutually exclusive)
})                               // → value, or UnsupportedType if decoding fails — check neo4j.isUnsupportedType(ssn)
```

Encryptable types: BOOLEAN, DATE, DURATION, FLOAT, INTEGER, homogeneous LIST, LOCAL DATETIME, LOCAL TIME, POINT, STRING, VECTOR, ZONED DATETIME, ZONED TIME, UUID, BYTES, NULL.

Same value encrypted twice → different bytes. Encrypted properties cannot be filtered, indexed, or compared server-side — query by plaintext key, decrypt in application.
