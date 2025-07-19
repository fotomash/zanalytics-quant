import streamlit as st
import os
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Parquet Config Utilities", page_icon="🔧", layout="wide")
st.header("🔧 Parquet Pair-Explorer (Folders → Pair → Files)")

folders = st.secrets.get("folders", {})

if not folders:
    st.error("No folders found in your secrets.toml. Please add them under a [folders] section.")
    st.stop()

# 1. First dropdown: folder
folder_name = st.selectbox("Select data folder", list(folders.keys()))
folder_path = folders[folder_name]

# 2. Second dropdown: pairs (subfolders in selected folder)
pair_folders = sorted([
    f.name for f in Path(folder_path).iterdir()
    if f.is_dir() and not f.name.startswith('.')
])

if not pair_folders:
    st.warning(f"No pair subfolders found in {folder_name} ({folder_path})")
    st.stop()

pair_name = st.selectbox("Select pair (symbol) subfolder", pair_folders)
pair_path = os.path.join(folder_path, pair_name)

# 3. List parquet files in selected pair folder
parquet_files = sorted(list(Path(pair_path).glob("*.parquet")))

if not parquet_files:
    st.warning(f"No Parquet files found in pair '{pair_name}' (folder: {pair_path})")
else:
    st.write(f"**Found {len(parquet_files)} Parquet files in `{pair_name}`**")
    for fpath in parquet_files:
        try:
            pq_file = pq.ParquetFile(str(fpath))
            colnames = pq_file.schema.names
            nrows = pq_file.metadata.num_rows if pq_file.metadata else "?"
            size_mb = fpath.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            with st.expander(f"📁 {fpath.name} | {nrows} rows | {size_mb:.2f} MB | Modified: {mtime}"):
                st.write(f"**Columns:** {colnames}")
                if st.button(f"Show first 5 rows: {fpath.name}", key=f"{pair_name}-{fpath}"):
                    try:
                        df = pd.read_parquet(str(fpath), engine="pyarrow")
                        st.dataframe(df.tail(5))
                    except Exception as e:
                        st.error(f"Could not preview data: {e}")
        except Exception as e:
            st.error(f"Failed to read {fpath}: {e}")

st.info("Select a folder, then a pair, to explore all available Parquet files.")