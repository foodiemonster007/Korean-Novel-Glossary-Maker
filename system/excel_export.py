# ===============================
# EXCEL EXPORT
# ===============================
"""
Handles Excel file creation and export
"""
import pandas as pd
from system import config_loader

def export_to_excel(excel_data, categories):
    """Export data to Excel file."""
    
    # Create DataFrame
    df = pd.DataFrame(excel_data)
    
    # Reorder columns based on SIMPLIFIED_CHINESE_CONVERSION flag
    if config_loader.SIMPLIFIED_CHINESE_CONVERSION:
        # Reorder to: "hangul", "hanja", "chinese", "english", "category", "frequency"
        column_order = ['hangul', 'hanja', 'chinese', 'english', 'category', 'frequency']
    else:
        # Reorder to: "hangul", "hanja", "english", "category", "frequency"
        column_order = ['hangul', 'hanja', 'english', 'category', 'frequency']
    
    df = df[column_order]
    
    # Save to Excel with category sheets
    try:
        output_excel = config_loader.OUTPUT_EXCEL
        print(f"\nSaving categorized data to a multi-sheet Excel file: '{output_excel}'")
        
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            for category in categories:
                df_cat = df[df['category'] == category]
                if not df_cat.empty:
                    # Drop category column for individual sheets
                    df_cat_to_write = df_cat.drop(columns=['category'])
                    sheet_name = category[:31]  # Excel sheet name limit
                    df_cat_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"  - Wrote {len(df_cat)} rows to sheet '{sheet_name}'.")
        
        print(f"\n✅ Successfully created sorted, categorized file: '{output_excel}'")
        
        # Also save a master sheet with all categories
        master_file = output_excel.replace('.xlsx', '_master.xlsx')
        with pd.ExcelWriter(master_file, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='All Nouns', index=False)
            print(f"✅ Created master file: '{master_file}'")
            
        return True
        
    except Exception as e:
        print(f"\nAn error occurred while saving the Excel file: {e}")
        return False