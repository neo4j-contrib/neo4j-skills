# Object Mapping and Repository Pattern

## Preview Mapping API

All mapping extension methods live in `Neo4j.Driver.Preview.Mapping`. Without this using directive, `AsObject<T>()` and `AsObjectsAsync<T>()` cause CS1061 compile errors.

```csharp
using Neo4j.Driver.Preview.Mapping;   // REQUIRED
```

## AsObject&lt;T&gt;() — Single Record

```csharp
public record Person(string Name, int Age);

var result = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

var person = result.Result[0].AsObject<Person>();
// RETURN key names map to property names (case-insensitive by default)
// 'name' → Name, 'age' → Age
```

C# `record` types work well — positional constructor parameters are matched by name.

## Blueprint Mapping (anonymous types)

```csharp
var person = result.Result[0].AsObjectFromBlueprint(new { name = "", age = 0 });
Console.WriteLine(person.name);   // "Alice"
Console.WriteLine(person.age);    // 21
```

## Lambda Mapping

```csharp
var person = result.Result[0].AsObject(
    (string name, int age) => new { Name = name, Age = age, BirthYear = 2025 - age });
```

## AsObjectsAsync&lt;T&gt;() — Bulk Mapping

```csharp
var (people, summary, _) = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .AsObjectsAsync<Person>();   // maps all records; returns EagerResult<IReadOnlyList<Person>>
```

---

## Repository Pattern Example

```csharp
public interface IPersonRepository
{
    Task<IReadOnlyList<Person>> FindByNamePrefixAsync(string prefix, CancellationToken ct = default);
    Task CreateAsync(Person person, CancellationToken ct = default);
    Task BulkCreateAsync(IEnumerable<Person> people, CancellationToken ct = default);
}

public class PersonRepository(IDriver driver, string database = "neo4j")
    : IPersonRepository
{
    public async Task<IReadOnlyList<Person>> FindByNamePrefixAsync(
        string prefix, CancellationToken ct = default)
    {
        var (records, _, _) = await driver
            .ExecutableQuery(@"
                MATCH (p:Person)
                WHERE p.name STARTS WITH $prefix
                RETURN p.name AS name, p.age AS age")
            .WithParameters(new { prefix })
            .WithConfig(new QueryConfig(database, RoutingControl.Readers))
            .ExecuteAsync(ct);

        return records
            .Select(r => new Person(r.Get<string>("name"), r.Get<int>("age")))
            .ToList();
    }

    public async Task CreateAsync(Person person, CancellationToken ct = default)
    {
        await driver
            .ExecutableQuery("CREATE (p:Person {name: $name, age: $age})")
            .WithParameters(new { name = person.Name, age = person.Age })
            .WithConfig(new QueryConfig(database))
            .ExecuteAsync(ct);
    }

    public async Task BulkCreateAsync(
        IEnumerable<Person> people, CancellationToken ct = default)
    {
        var rows = people
            .Select(p => new { name = p.Name, age = p.Age })
            .ToArray();

        await driver
            .ExecutableQuery(@"
                UNWIND $rows AS row
                MERGE (p:Person {name: row.name})
                SET p.age = row.age")
            .WithParameters(new { rows })
            .WithConfig(new QueryConfig(database))
            .ExecuteAsync(ct);
    }
}

public record Person(string Name, int Age);
```
