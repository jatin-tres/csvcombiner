"""
================================================================================
requirements.txt
================================================================================
streamlit==1.32.0
pandas==2.2.1
================================================================================
"""

import streamlit as st
import pandas as pd
import zipfile
import io
import os

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Raw CSV Stacker",
    page_icon="📋",
    layout="wide"
)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def read_single_csv(file_obj, filename: str) -> pd.DataFrame:
    """
    Reads a CSV as raw data, removes entirely blank rows/columns, 
    and forces a direct copy-paste stack.
    """
    try:
        # 1. Read raw data (treating headers as just another row)
        df = pd.read_csv(file_obj, header=None, dtype=str)
        
        # 2. REMOVE GHOST DATA: Drop columns and rows that are 100% empty
        # how='all' ensures it only drops if EVERY single cell in that row/column is blank
        df.dropna(axis=1, how='all', inplace=True)
        df.dropna(axis=0, how='all', inplace=True)
        
        # If the file was completely empty, skip it
        if df.empty:
            return None
            
        # 3. Rename the surviving columns to generic names so they stack perfectly
        df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
        
        # 4. Insert the filename as the very first column (Column A)
        df.insert(0, 'Source_File', filename)
        
        return df
        
    except pd.errors.EmptyDataError:
        # Silently skip files that contain absolutely zero bytes
        return None
    except Exception as e:
        st.error(f"Error reading file '{filename}': {e}")
        return None

def process_zip_file(zip_file_obj) -> list:
    dfs = []
    try:
        with zipfile.ZipFile(zip_file_obj, 'r') as z:
            csv_files = [f for f in z.infolist() if f.filename.endswith('.csv') and not f.filename.startswith('__MACOSX/')]
            
            for file_info in csv_files:
                with z.open(file_info) as f:
                    df = read_single_csv(f, f"{zip_file_obj.name} -> {os.path.basename(file_info.filename)}")
                    if df is not None:
                        dfs.append(df)
    except Exception as e:
        st.error(f"Error processing ZIP: {e}")
    return dfs

def process_uploaded_files(uploaded_files) -> pd.DataFrame:
    all_dfs = []
    
    progress_bar = st.progress(0, text="Copying, cleaning, and pasting data...")
    total = len(uploaded_files)
    
    for i, file in enumerate(uploaded_files):
        if file.name.lower().endswith('.csv'):
            df = read_single_csv(file, file.name)
            if df is not None:
                all_dfs.append(df)
        elif file.name.lower().endswith('.zip'):
            zip_dfs = process_zip_file(file)
            all_dfs.extend(zip_dfs)
            
        progress_bar.progress((i + 1) / total)
        
    progress_bar.empty()
    
    if not all_dfs:
        return None
        
    # Concatenate purely by position.
    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    # header=False prevents writing "Source_File, Column_1..." into the final output
    return df.to_csv(index=False, header=False).encode('utf-8')

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.title("📋 Raw CSV Stacker (Direct Copy-Paste)")
    st.markdown("Upload files to strictly stack them side-by-side. **Blank rows/columns are ignored**, and **Column A will be the filename.** Everything else is just copy-pasted starting from Column B.")

    uploaded_files = st.file_uploader("Upload CSV or ZIP files", type=['csv', 'zip'], accept_multiple_files=True)
    
    if st.button("Stack Data", type="primary"):
        if not uploaded_files:
            st.warning("Please upload a file first.")
            return
            
        st.session_state.combined_df = process_uploaded_files(uploaded_files)
        st.success("Data stacked and cleaned of empty rows!")

    if 'combined_df' in st.session_state and st.session_state.combined_df is not None:
        df = st.session_state.combined_df
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Real Rows Copied", f"{len(df):,}")
        with col2:
            st.metric("Total Columns Wide", f"{len(df.columns):,}")
        
        st.dataframe(df.head(100), use_container_width=True)
        
        st.download_button(
            label="⬇️ Download Stacked Data",
            data=convert_df_to_csv(df),
            file_name="stacked_data.csv",
            mime="text/csv",
            type="primary"
        )

if __name__ == "__main__":
    main()
