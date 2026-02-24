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
            # Filter out directories and MacOS metadata
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

def process_uploaded_files(uploaded_files) -> pd.DataFrame:
    """
    Processes a list of Streamlit UploadedFile objects (CSV or ZIP) 
    and combines them into a single DataFrame.
    """
    all_dfs = []
    total_files = len(uploaded_files)
    
    # Progress bar UI
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
            
        # Update progress
        progress_bar.progress((i + 1) / total_files, text=f"Processed {i+1} of {total_files} files...")
        
    progress_bar.empty() # Clear progress bar when done
    
    if not all_dfs:
        return None
        
    # Concatenate all dataframes
    # ignore_index=True resets the index.
    # missing columns between files will automatically be filled with NaN by pandas
    with st.spinner("Merging data..."):
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
    return combined_df

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """
    Converts a pandas DataFrame to a UTF-8 encoded CSV in memory.
    Cached to prevent re-computation on every UI interaction.
    """
    return df.to_csv(index=False).encode('utf-8')


# ==========================================
# MAIN APP LAYOUT & LOGIC
# ==========================================
def main():
    st.title("📄 CSV Combiner Pro")
    st.markdown("""
    **Combine multiple CSV files into a single, clean dataset.** Upload individual `.csv` files or a `.zip` file containing multiple CSVs. The app will automatically align columns, add a `source_file` tracking column, and handle missing values.
    """)

    # --- SESSION STATE INITIALIZATION ---
    if 'raw_combined_df' not in st.session_state:
        st.session_state.raw_combined_df = None
    if 'processed_df' not in st.session_state:
        st.session_state.processed_df = None

    # --- SIDEBAR UI ---
    with st.sidebar:
        st.header("1. Upload Files")
        uploaded_files = st.file_uploader(
            "Upload CSV or ZIP files", 
            type=['csv', 'zip'], 
            accept_multiple_files=True,
            help="You can drag and drop multiple files or a single ZIP archive here."
        )
        
        # Action Button to trigger processing
        process_button = st.button("Merge Files", type="primary", use_container_width=True)
        
        st.divider()
        st.header("2. Data Options")
        
        # Options are disabled if no data has been processed yet
        data_exists = st.session_state.raw_combined_df is not None
        
        remove_duplicates = st.checkbox("Remove Duplicate Rows", disabled=not data_exists)
        
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
            # Clear previous state
            st.session_state.raw_combined_df = None
            st.session_state.processed_df = None
            
            # Show list of uploaded files (Bonus feature)
            with st.expander("Show uploaded files details", expanded=False):
                st.write([f.name for f in uploaded_files])
            
            # Process files
            combined_df = process_uploaded_files(uploaded_files)
            
            if combined_df is not None:
                st.session_state.raw_combined_df = combined_df
                st.success("✅ Files successfully merged!")
            else:
                st.error("❌ Failed to merge files. Please check your data.")

    # --- DISPLAY & TRANSFORM LOGIC ---
    if st.session_state.raw_combined_df is not None:
        # 1. Apply user transformations to a copy of the raw data
        df = st.session_state.raw_combined_df.copy()
        
        if remove_duplicates:
            original_len = len(df)
            df = df.drop_duplicates()
            new_len = len(df)
            if original_len != new_len:
                st.info(f"🗑️ Removed {original_len - new_len} duplicate rows.")
                
        if sort_col != "None":
            try:
                df = df.sort_values(by=sort_col, ascending=sort_ascending)
            except Exception as e:
                st.warning(f"Could not sort by column '{sort_col}': {e}")
        
        st.session_state.processed_df = df

        # 2. Display Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", f"{len(df):,}")
        with col2:
            st.metric("Total Columns", f"{len(df.columns):,}")
        with col3:
            st.metric("Unique Source Files", f"{df['source_file'].nunique():,}")

        # 3. Display Data Preview
        st.subheader("Data Preview")
        st.dataframe(df.head(100), use_container_width=True) # Showing top 100 to save browser memory
        if len(df) > 100:
            st.caption(f"Showing first 100 rows out of {len(df):,} total rows.")

        # 4. Download Button
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
