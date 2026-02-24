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
    page_title="CSV Combiner Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def read_single_csv(file_obj, filename: str) -> pd.DataFrame:
    """
    Reads a single CSV file, adds the source_file column, and handles errors.
    """
    try:
        df = pd.read_csv(file_obj)
        df['source_file'] = filename
        return df
    except Exception as e:
        st.error(f"Error reading file '{filename}': {e}")
        return None

def process_zip_file(zip_file_obj) -> list:
    """
    Extracts and reads CSVs from a ZIP file in memory.
    """
    dfs = []
    try:
        with zipfile.ZipFile(zip_file_obj, 'r') as z:
            csv_files = [f for f in z.infolist() if f.filename.endswith('.csv') and not f.filename.startswith('__MACOSX/')]
            
            if not csv_files:
                st.warning(f"No CSV files found inside the ZIP: {zip_file_obj.name}")
                return dfs

            for file_info in csv_files:
                with z.open(file_info) as f:
                    df = read_single_csv(f, f"{zip_file_obj.name} -> {os.path.basename(file_info.filename)}")
                    if df is not None:
                        dfs.append(df)
    except zipfile.BadZipFile:
        st.error(f"The file {zip_file_obj.name} is not a valid ZIP file.")
    except Exception as e:
        st.error(f"Unexpected error processing ZIP {zip_file_obj.name}: {e}")
    
    return dfs

def process_uploaded_files(uploaded_files, join_strategy='outer') -> pd.DataFrame:
    """
    Processes a list of Streamlit UploadedFile objects and combines them.
    join_strategy: 'outer' keeps all columns, 'inner' keeps only shared columns.
    """
    all_dfs = []
    total_files = len(uploaded_files)
    
    progress_text = "Processing files. Please wait..."
    progress_bar = st.progress(0, text=progress_text)
    
    for i, file in enumerate(uploaded_files):
        if file.name.lower().endswith('.csv'):
            df = read_single_csv(file, file.name)
            if df is not None:
                all_dfs.append(df)
        elif file.name.lower().endswith('.zip'):
            zip_dfs = process_zip_file(file)
            all_dfs.extend(zip_dfs)
        else:
            st.warning(f"Skipped unsupported file format: {file.name}")
            
        progress_bar.progress((i + 1) / total_files, text=f"Processed {i+1} of {total_files} files...")
        
    progress_bar.empty()
    
    if not all_dfs:
        return None
        
    with st.spinner("Merging data..."):
        # NEW: join parameter controls whether we keep all columns or just common ones
        combined_df = pd.concat(all_dfs, ignore_index=True, join=join_strategy)
        
    return combined_df

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """
    Converts a pandas DataFrame to a UTF-8 encoded CSV in memory.
    """
    return df.to_csv(index=False).encode('utf-8')

# ==========================================
# MAIN APP LAYOUT & LOGIC
# ==========================================
def main():
    st.title("📄 CSV Combiner Pro")
    st.markdown("""
    **Combine multiple CSV files into a single, clean dataset.** Upload individual `.csv` files or a `.zip` file containing multiple CSVs. 
    You can now dynamically filter out extra columns caused by mismatched files.
    """)

    # --- SESSION STATE INITIALIZATION ---
    if 'raw_combined_df' not in st.session_state:
        st.session_state.raw_combined_df = None

    # --- SIDEBAR UI ---
    with st.sidebar:
        st.header("1. Upload Files")
        uploaded_files = st.file_uploader(
            "Upload CSV or ZIP files", 
            type=['csv', 'zip'], 
            accept_multiple_files=True
        )
        
        st.header("2. Merge Strategy")
        merge_type = st.radio(
            "How should columns be combined?",
            options=["Keep ALL columns (Union)", "Keep ONLY common columns (Intersection)"],
            help="If your files have different columns, keeping ALL columns will result in empty (None) values for some rows. Keeping ONLY common columns guarantees no extra mismatched columns are added."
        )
        
        # Determine the pandas join string based on user selection
        join_str = 'outer' if "ALL" in merge_type else 'inner'
        
        process_button = st.button("Merge Files", type="primary", use_container_width=True)
        
        st.divider()
        st.header("3. Data Cleaning Options")
        
        data_exists = st.session_state.raw_combined_df is not None
        
        remove_duplicates = st.checkbox("Remove Duplicate Rows", disabled=not data_exists)
        
        # NEW: Slider to drop columns based on missing values
        st.subheader("Filter Empty Columns")
        missing_threshold = st.slider(
            "Drop columns missing more than (%)", 
            min_value=0, max_value=100, value=100, step=5,
            disabled=not data_exists,
            help="Set to 100% to keep all columns. Set to 50% to drop columns where more than half the rows are empty."
        )
        
        sort_col = st.selectbox(
            "Sort by Column (Optional)", 
            options=["None"] + (list(st.session_state.raw_combined_df.columns) if data_exists else []),
            disabled=not data_exists
        )
        sort_ascending = st.checkbox("Ascending Order", value=True, disabled=not data_exists or sort_col == "None")

    # --- PROCESSING LOGIC ---
    if process_button:
        if not uploaded_files:
            st.warning("⚠️ Please upload at least one CSV or ZIP file before merging.")
        else:
            st.session_state.raw_combined_df = None
            
            with st.expander("Show uploaded files details", expanded=False):
                st.write([f.name for f in uploaded_files])
            
            combined_df = process_uploaded_files(uploaded_files, join_strategy=join_str)
            
            if combined_df is not None:
                st.session_state.raw_combined_df = combined_df
                st.success("✅ Files successfully merged!")
            else:
                st.error("❌ Failed to merge files. Please check your data.")

    # --- DISPLAY & TRANSFORM LOGIC ---
    if st.session_state.raw_combined_df is not None:
        df = st.session_state.raw_combined_df.copy()
        
        # --- NEW: Drop columns based on missing values threshold ---
        if missing_threshold < 100:
            # Calculate the percentage of missing values per column
            missing_percentages = df.isnull().mean() * 100
            # Keep only columns where the missing percentage is less than or equal to the threshold
            cols_to_keep = missing_percentages[missing_percentages <= missing_threshold].index
            
            dropped_count = len(df.columns) - len(cols_to_keep)
            df = df[cols_to_keep]
            
            if dropped_count > 0:
                st.info(f"🧹 Dropped {dropped_count} column(s) that exceeded the {missing_threshold}% missing data threshold.")
        
        # Apply standard transformations
        if remove_duplicates:
            original_len = len(df)
            df = df.drop_duplicates()
            if original_len != len(df):
                st.info(f"🗑️ Removed {original_len - len(df)} duplicate rows.")
                
        if sort_col != "None" and sort_col in df.columns:
            try:
                df = df.sort_values(by=sort_col, ascending=sort_ascending)
            except Exception as e:
                st.warning(f"Could not sort by column '{sort_col}': {e}")

        # Display Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", f"{len(df):,}")
        with col2:
            st.metric("Total Columns", f"{len(df.columns):,}")
        with col3:
            st.metric("Unique Source Files", f"{df['source_file'].nunique():,}")

        # Display Data Preview
        st.subheader("Data Preview")
        st.dataframe(df.head(100), use_container_width=True)
        if len(df) > 100:
            st.caption(f"Showing first 100 rows out of {len(df):,} total rows.")

        # Download Button
        st.subheader("Download Merged Data")
        csv_data = convert_df_to_csv(df)
        
        st.download_button(
            label="⬇️ Download Combined CSV",
            data=csv_data,
            file_name="combined_dataset.csv",
            mime="text/csv",
            type="primary"
        )

if __name__ == "__main__":
    main()
