# ncOSCore Strategy Research Bundle (SRB) System

## Overview
The SRB system provides a hybrid offline-online architecture for efficient strategy simulation, session memory restoration, and seamless data management within the ncOSCore framework.

## Key Features
- **Exportable Snapshots** - Efficient data export with indexing and merging
- **Unified Instructions** - Single reference point for all system configurations  
- **Virtual File Mapping** - Transparent access to distributed data
- **Session Memory Restoration** - Delta-based session state management
- **Multi-Timeframe Support** - Optimized storage for tick and aggregated data

## Quick Start
```bash
# 1. Extract the SRB DevKit
tar -xzf ncOS_SRB_DevKit_v1.0.tar.gz
cd ncOS_SRB_DevKit_v1.0

# 2. Run setup
./scripts/setup.sh

# 3. Test the system
python examples/srb_implementation.py
```

## Architecture
- **Hybrid Design** - Works both offline and online
- **Vector Integration** - Semantic search capabilities
- **Parquet Storage** - Efficient columnar format
- **Delta Sessions** - Incremental state management

## Documentation
- `docs/SRB_System_Design.md` - Complete system design
- `instructions.md` - Unified configuration reference
- `examples/` - Working code examples

## Support
For questions or issues, consult the documentation or contact the ncOSCore team.
