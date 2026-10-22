Pass `idempotency_key` through on `add_memory` so retries and replayed tool calls dedupe server-side instead of creating duplicate memories.
