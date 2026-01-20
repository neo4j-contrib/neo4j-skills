---
name: neo4j-migration-skill
description: Use when upgrading Neo4j drivers to new major versions
allowed-tools: WebFetch
---

# Neo4j migration skill

This skill uses online guides to upgrade old Neo4j codebases. It handles all official Neo4j drivers.

## When to use

Use this skill when:
- a user asks to upgrade a Neo4j driver in languages: .NET, Go, Java, Javascript, Python

## Instructions

1. At the beginning, ALWAYS ask a user what Neo4j version is going to be used after the upgrade. Note, the Neo4j database's version is not upgraded as part of this skill, we just need that information
    a) If the user says that most recent, fetch the version from the [supported version list](https://neo4j.com/developer/kb/neo4j-supported-versions/) along with the most recent driver version
    b) Otherwise, analyze the [supported versions list](https://neo4j.com/developer/kb/neo4j-supported-versions/) and choose the most recent driver version for given Neo4j version

2. Analyze the codebase in order to determine what additional documentation to include, focus only on dependencies' files (e.g. `package.json`, `requirements.txt`, `pom.xml` etc.). If the codebase uses Neo4j driver for:
    - .NET then include [.NET migration guide](references/dotnet-driver.md)
    - Go then include [Go migration guide](references/go-driver.md)
    - Java then include [Java migration guide](references/java-driver.md)
    - Javascript/Node.JS then include [Javascript migration guide](references/javascript-driver.md)
    - Python then include [Python migration guide](references/python-driver.md)

Important: when you plan the upgrade, always include replacement of deprecated functions in the plan