# Property Encryption [v6.4.0+, preview]

Client-side envelope encryption of property values. Server-version agnostic — ciphertext stored as `[]byte` property. Cross-driver interoperable (Java, JS, Go) when profiles match. Preview: API may change without deprecation cycle.

Package: `github.com/neo4j/neo4j-go-driver/v6/neo4j/propertyencryption` · Example: [`encryption_example_test.go`](https://github.com/neo4j/neo4j-go-driver/blob/v6.4.0/neo4j/propertyencryption/encryption_example_test.go)

## Crypto parameters (fixed)

| Item | Value |
|---|---|
| Data key | AES-256 |
| Algorithm | AES-GCM |
| AAD | optional; must match on decrypt |

## Components

| Component | Provided by | Role |
|---|---|---|
| `KeyEncapsulationService` | driver (`propertyencryption.NewLocalKeyEncapsulationService(kek)`, 32-byte `kek`) or user (KMS) | `Encapsulate(ctx, options)` / `Decapsulate(ctx, encapsulation, metadata)` data keys |
| `EncapsulatedKeyRecordRepository` | **user** — no built-in | persist `EncapsulatedKeyRecord`; unique immutable `ID`; unique alias. Methods: `FindByID`, `FindByAlias`, `Create(ctx, alias, encapsulation, metadata)`, `SetAlias`, `DeleteByID`. Not found → return `propertyencryption.ErrKeyNotFound` |
| `propertyencryption.EnvelopeProfile` | driver | `Name` (stored with each value; must match on every reading driver), `EncapsulationService`, `KeyRepository` required. Optional: `KeyCacheTTL`, `KeyCacheSize`, `KeyAliasIndexTTL` (alias rotation delay), `KeyAliasIndexSize`, `DisableKeyCache` |

## Setup

```go
keyService, err := propertyencryption.NewLocalKeyEncapsulationService(kek) // kek from secret store, never hardcode
if err != nil { return err }

driver, err := neo4j.NewDriver(uri, neo4j.BasicAuth(user, password, ""),
    func(c *config.Config) {
        c.PropertyEncryptionProfiles = []propertyencryption.Profile{
            propertyencryption.EnvelopeProfile{
                Name:                 "customer-pii",
                EncapsulationService: keyService,
                KeyRepository:        keyRepo, // your EncapsulatedKeyRecordRepository
            },
        }
    })
if err != nil { return err }
defer driver.Close(ctx)

enc := driver.PropertyEncryption() // no connection needed; propertyencryption.New(profiles) works without driver

// Create data key once — must exist before encrypting
keys, err := enc.Keys("customer-pii")
if err != nil { return err }
if _, err := keys.Create(ctx, "current", nil); err != nil { return err } // also FindByAlias, SetAlias, DeleteAlias, DeleteByID
```

## Encrypt / store / decrypt

```go
ssnEnc, err := enc.EncryptWithAAD(ctx, propertyencryption.EncryptRequest{
    Value:   "078-05-1120",
    Key:     propertyencryption.KeyAlias("current"), // or KeyID(id) to pin
    Profile: "customer-pii",                         // optional when 1 profile
}, "customer-1") // AAD: bool, string, integer, []byte, Date, LocalTime, Time, Point2D/3D, UUID
if err != nil { return err }

_, err = neo4j.ExecuteQuery(ctx, driver,
    "MERGE (c:Customer {id: $id}) SET c.ssnEnc = $enc",
    map[string]any{"id": "customer-1", "enc": ssnEnc},
    neo4j.EagerResultTransformer, neo4j.ExecuteQueryWithDatabase(database))

res, err := neo4j.ExecuteQuery(ctx, driver,
    "MATCH (c:Customer {id: $id}) RETURN c.ssnEnc AS enc",
    map[string]any{"id": "customer-1"},
    neo4j.EagerResultTransformer, neo4j.ExecuteQueryWithDatabase(database),
    neo4j.ExecuteQueryWithReadersRouting())
if err != nil { return err }
stored, _, err := neo4j.GetRecordValue[[]byte](res.Records[0], "enc")
if err != nil { return err }

ssn, err := enc.DecryptWithAAD(ctx, stored, "customer-1") // Decrypt(ctx, b) uses AAD stored with value
if neo4j.IsPropertyEncryptionError(err) { /* wrong AAD, missing key, tampered bytes */ }
```

Unknown type/encoding decrypts to `*dbtype.UnsupportedType`, not error. AAD not Unicode-normalised — normalise strings on both sides.

Same value encrypted twice → different bytes. Encrypted properties cannot be filtered, indexed, or compared in Cypher — query by plaintext key, decrypt in application.
