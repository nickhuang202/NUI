import pandas as pd
import sys
import os

def convert_all_sheets_to_csv(xlsx_file):
    try:
        # 取得檔案的基本名稱 (不含副檔名)，用來當作輸出的前綴
        base_name = os.path.splitext(os.path.basename(xlsx_file))[0]

        print(f"正在讀取 Excel 檔案: {xlsx_file} ...")

        # 關鍵參數: sheet_name=None 代表讀取 "所有" Sheet
        # 這會回傳一個 dict: {'Sheet1': df1, 'Sheet2': df2, ...}
        all_sheets = pd.read_excel(xlsx_file, sheet_name=None)

        for sheet_name, df in all_sheets.items():
            # 建立輸出的檔名: 原檔名_Sheet名.csv
            # 為了避免檔名有空白，將空白換成底線 (可選)
            safe_sheet_name = sheet_name.replace(" ", "_")
            csv_filename = f"{base_name}_{safe_sheet_name}.csv"

            # 轉存 CSV
            df.to_csv(csv_filename, index=False, encoding='utf-8')
            print(f"✅ 已輸出: {csv_filename} (筆數: {len(df)})")

        print("\n全部轉換完成！")

    except FileNotFoundError:
        print(f"❌ 找不到檔案: {xlsx_file}")
    except ImportError:
        print("❌ 錯誤: 請確認已安裝 pandas 與 openpyxl (pip install pandas openpyxl)")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方式: python3 xlsx2csv_all.py <excel_file.xlsx>")
    else:
        convert_all_sheets_to_csv(sys.argv[1])
