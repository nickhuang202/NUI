import os
import argparse
import sys
import pandas as pd

def split_test_logs(source_file):
    """
    Step 1: Split the Log file.
    Returns: The path of the output directory (output_dir).
    """
    # 1. Check if source file exists
    if not os.path.exists(source_file):
        print(f"Error: File '{source_file}' not found.")
        sys.exit(1)

    # 2. Generate output directory name
    base_name = os.path.basename(source_file)
    file_name_no_ext = os.path.splitext(base_name)[0]
    
    # Create output directory path
    output_dir = f"{file_name_no_ext}_split_logs"

    # 3. Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[Split] Created output directory: {output_dir}")
    else:
        print(f"[Split] Using existing directory: {output_dir}")

    # Define markers
    START_MARKER = "########## Running test:"
    END_MARKER = "Running all tests took"
    
    current_file = None
    file_count = 0

    print(f"[Split] Processing file: {source_file} ...")

    try:
        with open(source_file, 'r', encoding='utf-8', errors='replace') as infile:
            for line in infile:
                
                # --- Check for end marker ---
                if END_MARKER in line:
                    break

                # --- Check for start marker ---
                if START_MARKER in line:
                    if current_file:
                        current_file.close()
                    
                    parts = line.split(START_MARKER)
                    if len(parts) > 1:
                        test_name = parts[1].strip()
                        # Sanitize filename 
                        # (Replace path separators to prevent 'File Not Found' errors)
                        safe_filename = test_name.replace("/", "_").replace("\\", "_")
                        
                        output_path = os.path.join(output_dir, f"{safe_filename}.log")
                        current_file = open(output_path, 'w', encoding='utf-8')
                        file_count += 1

                # --- Write content ---
                if current_file:
                    current_file.write(line)

    except Exception as e:
        print(f"[Split] Error: {e}")
    finally:
        if current_file:
            current_file.close()

    print(f"[Split] Done. {file_count} log files generated.")
    
    # Important: Return the generated directory path for the next step
    return output_dir

def generate_excel_report(log_dir):
    """
    Step 2: Read the split folder and generate an Excel report.
    """
    if not os.path.exists(log_dir):
        print(f"[Report] Error: Directory '{log_dir}' not found.")
        return

    data = []
    # Only grab .log files in the directory
    files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    
    print(f"[Report] Scanning {len(files)} files in '{log_dir}'...")

    for filename in files:
        file_path = os.path.join(log_dir, filename)
        status = "PASS"
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                # Check for failure keywords
                if "[   FAILED ]" in content:
                    status = "FAIL"
        except Exception:
            status = "ERROR"

        # Excel Hyperlink Formula
        # Uses relative path so links work if the folder is moved (as long as structure is maintained)
        hyperlink_formula = f'=HYPERLINK("{os.path.join(log_dir, filename)}", "Open Log")'

        data.append({
            "Test Name": filename.replace(".log", ""),
            "Status": status,
            "Log Link": hyperlink_formula
        })

    # Check if any data was collected
    if not data:
        print("[Report] No log files found to report.")
        return

    # Create DataFrame
    df = pd.DataFrame(data)
    output_excel = f"{log_dir}_report.xlsx"

    # Write to Excel
    try:
        writer = pd.ExcelWriter(output_excel, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Test Results')

        workbook = writer.book
        worksheet = writer.sheets['Test Results']

        # Define Formats
        red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        
        # Set Column Widths
        worksheet.set_column('A:A', 50) # Test Name
        worksheet.set_column('B:B', 10) # Status
        worksheet.set_column('C:C', 15) # Link

        # Conditional Formatting
        row_count = len(df) + 1
        
        # If Status is FAIL -> Red
        worksheet.conditional_format(f'B2:B{row_count}', {
            'type': 'cell', 'criteria': 'equal to', 'value': '"FAIL"', 'format': red_format
        })
        # If Status is PASS -> Green
        worksheet.conditional_format(f'B2:B{row_count}', {
            'type': 'cell', 'criteria': 'equal to', 'value': '"PASS"', 'format': green_format
        })

        writer.close()
        print(f"[Report] Excel report generated successfully!")
        print(f"Report File: {os.path.abspath(output_excel)}")
        
    except Exception as e:
        print(f"[Report] Failed to create Excel: {e}")

# --- Main Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split logs and generate Excel report.")
    parser.add_argument("input_file", help="Path to the original big log file")
    
    args = parser.parse_args()

    # 1. Execute split and get the generated folder name
    generated_folder = split_test_logs(args.input_file)
    
    # 2. Pass the folder name to the Excel generator
    generate_excel_report(generated_folder)