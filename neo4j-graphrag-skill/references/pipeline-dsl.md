# Dataflow Pipeline DSL + Observers [v1.21+; 1.20 never released]

Lazy: nothing runs until `collect()`, iteration, `to_sink()`, or `Interpreter.evaluate()`. Text splitters expose `iter_chunks(text)` → `Iterator[TextChunk]`.

```python
from neo4j_graphrag.pipeline import LocalInterpreter, LoggingStageObserver, Pipeline, Source

class TextSource(Source[str]):              # from_source() takes a Source, not a list
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
    def read(self) -> list[str]:            # called on every evaluation
        return list(self._texts)

pipeline = (
    Pipeline.from_source(TextSource(texts))
    .flat_map(splitter.iter_chunks, label="split")
    .map(embed_chunk, label="embed")        # label= names stage in observer output
)
results = pipeline.collect()                # default LocalInterpreter, no observers

# Observers attach to the interpreter, not the pipeline
interp = LocalInterpreter(observers=[LoggingStageObserver()])
results = list(interp.evaluate(pipeline))
pipeline.to_sink(my_sink, interpreter=interp)  # sink-terminated: pass interpreter here
```

Custom hooks: subclass `StageObserver` (`before` / `after` per item per stage, `on_error` once per failing stage).
