Act as a senior Python developer and Streamlit expert.

Build a complete, production-ready Streamlit app that does the following:

OBJECTIVE:
Create a tool where a user can either:
1) Upload multiple CSV files manually, OR
2) Upload a ZIP file containing multiple CSV files

FUNCTIONALITY:
- Read all CSV files
- Combine (append/concatenate) them into one single DataFrame
- Add a new column named "source_file"
- This column must contain the original file name from which each row came
- Preserve all original columns
- If columns differ between files, handle it gracefully by aligning columns and filling missing values with NaN
- Display preview of combined data
- Show total number of rows combined
- Provide a download button to download the merged CSV

UI REQUIREMENTS:
- Clean Streamlit layout
- Clear instructions for user
- Progress indicator while processing files
- Error handling if non-CSV files are uploaded
- Show warning if no files uploaded

TECHNICAL REQUIREMENTS:
- Use pandas for data processing
- Efficient memory handling
- Modular code structure (separate logic functions)
- Well-commented code
- Ready-to-run script (single app.py file)
- Include requirements.txt content

BONUS:
- Show list of uploaded file names before merging
- Option to remove duplicate rows
- Option to sort by selected column

Return only the full working code.
