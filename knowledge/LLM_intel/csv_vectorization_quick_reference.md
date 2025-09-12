# CSV to Vector Pipeline - Quick Reference

## Error Handling Features

### 1. **Automatic Retry**
- 3 attempts with exponential backoff
- Configurable via `@retry` decorator

### 2. **Circuit Breaker**
- Triggers after 5 consecutive errors
- Prevents system overload

### 3. **Data Validation**
- Column existence checking
- Data type coercion with fallbacks
- Bounds checking for all calculations

### 4. **Error Metrics**
- Real-time tracking of failures
- Success rate monitoring
- Detailed error categorization

### 5. **Graceful Degradation**
- Continues processing with partial data
- Returns minimal valid responses on error
- Logs all issues for debugging

## Usage Examples

```python
from csv_to_vector_integrated import CSVVectorizer, process_csv_file

# Initialize
vectorizer = CSVVectorizer(
    window_size="1T",
    namespace="csv_vector_memory"
)

# Process single chunk
result = vectorizer.process_csv_chunk(df)
if result['vector_ready']:
    print(result['summary'])

# Process entire file
results = process_csv_file('tick_data.csv', vectorizer)
print(f"Status: {results['status']}")
print(f"Success rate: {results['metrics']['success_rate']:.2%}")
```

## Error Types

1. **DataLoadingError** - File access issues
2. **DataQualityError** - Invalid data format
3. **VectorizationError** - Processing failures

## Monitoring

Check logs at: `logs/csv_vectorization.log`
