# ncOSCore SRB System Instructions

## System Overview
The Strategy Research Bundle (SRB) system provides unified instructions for all components within the ncOSCore framework.

## Configuration
```yaml
srb_system:
  version: "1.0"
  mode: "hybrid" # offline/online/hybrid
  data_ingestion:
    auto_extract: true
    archive_formats: [".tar.gz", ".zip", ".7z"]
    extraction_path: "/data/extracted"
    create_virtual_map: true
    notify_agents: true
  snapshot_export:
    format: "parquet"
    compression: "zstd"
    compression_level: 3
    include_metadata: true
    include_vectors: true
    chunk_size: 100000
  session_memory:
    delta_format: "json"
    compression: "zstd"
    max_delta_size: "10MB"
    retention_days: 30
    auto_checkpoint: true
    checkpoint_interval: 3600 # seconds
  virtual_file_system:
    enable: true
    index_metadata: true
    cache_size: "1GB"
    eviction_policy: "lru"
```

## Agent Specifications
```json
{
  "agent_registry": {
    "DataIngestionAgent": {
      "class": "agents.DataIngestionAgent",
      "triggers": ["file_upload", "archive_detected"],
      "file_patterns": ["*.tar.gz", "*.zip"],
      "actions": {
        "extract": {
          "timeout": 300,
          "max_size": "5GB"
        },
        "index": {
          "create_vectors": true,
          "extract_metadata": true
        },
        "notify": {
          "broadcast": true,
          "include_summary": true
        }
      }
    },
    "SnapshotAgent": {
      "class": "agents.SnapshotAgent",
      "schedule": "0 */4 * * *",
      "triggers": ["manual", "threshold"],
      "thresholds": {
        "data_size": "1GB",
        "record_count": 1000000,
        "time_elapsed": 14400
      },
      "export_config": {
        "include_deltas": true,
        "compress": true,
        "sign": true
      }
    }
  }
}
```

## Virtual File Mapping
```yaml
virtual_file_map:
  version: "1.0"
  mappings:
    "/data/tick/{symbol}/{date}":
      physical: "/storage/parquet/tick/{symbol}/year={year}/month={month}/day={day}"
      format: "parquet"
      compression: "snappy"
    "/data/timeframe/{timeframe}/{symbol}":
      physical: "/storage/parquet/timeframe/{timeframe}/{symbol}"
      format: "parquet"
      compression: "snappy"
```

## Operational Procedures

### Data Ingestion
1. Archive detected → DataIngestionAgent triggered
2. Extract to temporary location
3. Validate and enrich data
4. Create vector embeddings
5. Store in virtual file system
6. Update virtual file map
7. Notify all agents

### Snapshot Creation
1. Collect data from all sources
2. Merge incremental changes
3. Compress using zstd
4. Generate manifest
5. Sign package
6. Export to designated location

### Session Restoration
1. Load session delta JSON
2. Verify integrity
3. Apply deltas in sequence
4. Restore agent states
5. Rebuild virtual file map
6. Resume operations
