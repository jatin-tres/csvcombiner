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
    Reads a CSV as raw data (ignoring headers) to force a direct copy-paste stack.
    """
    try:
        # header=None tells pandas to treat the actual column names as just another row of data
        # dtype=str ensures it just copies the text exactly as it is without trying to interpret it
        df = pd.read_csv(file_obj, header=None, dtype=str)
        
        # Rename the columns to generic names (Column_1, Column_2, etc.) so they stack perfectly
        df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
        
        # Insert the filename as the very first column (Column A)
        df.insert(0, 'Source_File', filename)
        
        return df
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
    
    progress_bar = st.progress(0, text="Copying and pasting data...")
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
    # If Sheet 1 has 10 columns and Sheet 2 has 12 columns, 
    # they will simply stack starting from Column B.
    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    # header=False prevents writing "Source_File, Column_1, Column_2..." into the final output
    return df.to_csv(index=False, header=False).encode('utf-8')

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.title("📋 Raw CSV Stacker (Direct Copy-Paste)")
    st.markdown("Upload files to strictly stack them side-by-side. **Column A will be the filename**, and everything else is just copy-pasted starting from Column B.")

    uploaded_files = st.file_uploader("Upload CSV or ZIP files", type=['csv', 'zip'], accept_multiple_files=True)
    
    if st.button("Stack Data", type="primary"):
        if not uploaded_files:
            st.warning("Please upload a file first.")
            return
            
        st.session_state.combined_df = process_uploaded_files(uploaded_files)
        st.success("Data stacked!")

    if 'combined_df' in st.session_state and st.session_state.combined_df is not None:
        df = st.session_state.combined_df
        
        st.metric("Total Rows Copied", len(df))
        
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
