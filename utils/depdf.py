import pikepdf
import os
from pathlib import Path

def batch_unlock_pdfs(input_folder, output_folder, password):
    # 確保輸出資料夾存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"建立輸出資料夾：{output_folder}")

    # 取得所有 PDF 檔案
    pdf_files = list(Path(input_folder).glob("*.pdf"))

    if not pdf_files:
        print("在指定資料夾內找不到 PDF 檔案。")
        return

    print(f"開始處理 {len(pdf_files)} 個檔案...")

    for pdf_path in pdf_files:
        try:
            # 嘗試開啟並解密
            with pikepdf.open(pdf_path, password=password) as pdf:
                output_path = os.path.join(output_folder, f"unlocked_{pdf_path.name}")
                pdf.save(output_path)
                print(f"✅ 成功解鎖：{pdf_path.name}")

        except pikepdf.PasswordError:
            print(f"❌ 密碼錯誤，跳過檔案：{pdf_path.name}")
        except Exception as e:
            print(f"⚠️ 處理 {pdf_path.name} 時發生錯誤：{e}")

if __name__ == "__main__":
    # --- 請在此修改你的參數 ---
    SOURCE_DIR = "./protected_pdfs"  # 存放加密 PDF 的資料夾
    TARGET_DIR = "./unlocked_pdfs"   # 解密後的存放位置
    #MY_PASSWORD = "abcd1234"         # 這些檔案共同擁有的密碼
    MY_PASSWORD = "docs1234"         # 這些檔案共同擁有的密碼
    # -----------------------

    batch_unlock_pdfs(SOURCE_DIR, TARGET_DIR, MY_PASSWORD)
    print("\n任務完成！")
