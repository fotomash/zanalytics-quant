# Replay Inspector CLI

`scripts/replay_inspector.py` inspects Parquet replays with optional filtering
and analog scoring. The CLI loads tick or bar data, filters rows with a pandas
`query`, enriches the resulting DataFrame and scores rows using vector
similarity. The scoring can be seeded with custom text or defaults to the first
row in the dataset.

## Usage

```bash
python scripts/replay_inspector.py path/to/data.parquet [--filter "symbol == 'EURUSD'"] [--query "spike down"] [--top 3]
```

### Key options

- `--filter`: pandas `query` expression applied before enrichment.
- `--columns`: space-delimited columns used to build the embedding text. If not
  provided, all columns are used.
- `--query`: seed text for analog scoring. When omitted the first row is used as
  the query vector.
- `--top`: number of results to display (default `5`).

## Filtering example

Filter ticks for a single symbol and price threshold:

```bash
python scripts/replay_inspector.py ticks.parquet --filter "symbol == 'BTCUSDT' and price > 40000"
```

## Analog scoring examples

Seed the analog scoring with custom text:

```bash
python scripts/replay_inspector.py ticks.parquet --query "flash crash" --top 3
```

Score using only specific columns:

```bash
python scripts/replay_inspector.py ticks.parquet --columns price volume --query "spike up"
```

The script prints the row index and cosine similarity score for the top
matches:

```
row=17 score=0.8901
row=42 score=0.8543
row=5  score=0.8322
```
