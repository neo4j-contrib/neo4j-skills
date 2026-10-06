# Property Encryption [6.3.0+, preview]

Client-side envelope encryption of property values. Server-version agnostic — encrypted value stored as `BYTES` property. Cross-driver interoperable when drivers use compatible profiles. Preview: API may change without deprecation cycle.

Source: [Property Encryption discussion #1786](https://github.com/neo4j/neo4j-java-driver/discussions/1786) · [6.3 API docs](https://neo4j.com/docs/api/java-driver/6.3)

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
| `KeyEncapsulationService` / `AsyncKeyEncapsulationService` | driver or user | generate + encapsulate/decapsulate AES-256 data keys |
| `EncapsulatedKeyRecordRepository` / `Async…` | **user** — no built-in | persist encapsulated keys; assign globally unique immutable ids; enforce alias uniqueness. Methods: `create`, `findById`, `findByAlias`, `setAliasById`, `deleteById` |
| `EnvelopePropertyEncryptionProfile` | driver | named profile; name stored with each encrypted value |

Key encapsulation services:

| Service | Artifact |
|---|---|
| `KeyEncapsulationServices.local(masterKey)` — AES-256 `SecretKey` master key | `neo4j-java-driver` |
| AWS KMS (`AwsKeyEncapsulationOptions.of(keyId)`) | `neo4j-java-driver-encryption-aws-kms` |
| Azure Key Vault | `neo4j-java-driver-encryption-azure-keyvault` |
| Google Cloud KMS | `neo4j-java-driver-encryption-google-cloud-kms` |

Manage module versions with BOM:
```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.neo4j.driver</groupId>
      <artifactId>neo4j-java-driver-bom</artifactId>
      <version>6.3.0</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>
```

## Setup

```java
var encapsulationService = KeyEncapsulationServices.local(masterKey);   // load master key from secret store, never hardcode
var profile = EnvelopePropertyEncryptionProfile
        .builder("users-profile", encapsulationService, keyRepository)  // keyRepository: your EncapsulatedKeyRecordRepository
        .withKeyCache(100, Duration.ofHours(1))                          // default on; .withoutKeyCache() disables
        .build();

var config = Config.builder()
        .withPropertyEncryptionProfiles(profile)   // one or many; names must be unique
        .build();
var driver = GraphDatabase.driver(uri, AuthTokens.basic(user, password), config);

PropertyEncryption propertyEncryption = driver.propertyEncryption();
// async / reactive: driver.propertyEncryption(AsyncPropertyEncryption.class)
```

Create data key once (must exist before encrypting):
```java
var keyManager = propertyEncryption.keyManager();              // keyManager("profile-name") when >1 profile
EncapsulatedKey key = keyManager.create("users-key");          // alias "users-key"
keyManager.findByAlias("users-key");                           // Optional<EncapsulatedKey>
```

## Encrypt / store / decrypt

```java
var encrypted = propertyEncryption.encryptToBytes(PropertyEncryptionRequest.builder()
        .fromValue(ssn)
        .withAAD(userId)                  // bind ciphertext to context; non-secret
        .usingKeyAlias("users-key")       // or usingKeyId(id); usingProfile(name) required when >1 profile
        .build());

driver.executableQuery("MATCH (u:User {id: $id}) SET u.ssnEnc = $enc")
        .withParameters(Map.of("id", userId, "enc", encrypted))
        .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
        .execute();

byte[] stored = driver.executableQuery("MATCH (u:User {id: $id}) RETURN u.ssnEnc AS enc")
        .withParameters(Map.of("id", userId))
        .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
        .execute().records().get(0).get("enc").asByteArray();
Value ssnValue = propertyEncryption.decrypt(PropertyDecryptionRequest.builder()
        .fromValue(stored)
        .withAAD(userId)                  // same AAD, else decrypt fails; withoutExternalAAD() if none used
        .build());
```

Ciphertext always references immutable key id, even when encrypted via alias — re-pointing alias does not break old values.

Encryptable types: BOOLEAN, DATE, DURATION, FLOAT, INTEGER, homogeneous LIST, LOCAL DATETIME, LOCAL TIME, POINT, STRING, VECTOR, ZONED DATETIME, ZONED TIME, UUID, BYTES, NULL.
AAD types: DATE, INTEGER, LOCAL TIME, POINT, STRING (NFC-normalize both sides), ZONED TIME, UUID, BYTES. Never put secrets in AAD.

Encrypted properties cannot be filtered, indexed, or compared server-side — query by a plaintext key, decrypt in application.
