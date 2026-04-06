"""
PDF 處理與文字擷取模組
使用 PyMuPDF 提取乾淨文字，自動移除頁首頁尾、目錄、浮水印、頁碼等
最適合 NotebookLM 使用的乾淨文字輸出
"""

import io
import re
import os
import logging
import tempfile
from datetime import datetime
from typing import Optional, Tuple

import requests
import pymupdf  # PyMuPDF

logger = logging.getLogger(__name__)

# 下載設定
DOWNLOAD_TIMEOUT = 60  # 秒
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}


def download_pdf(url: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    下載 PDF 檔案

    Returns:
        (pdf_bytes, error_message) - 成功時 error_message 為 None
    """
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=DOWNLOAD_TIMEOUT,
            stream=True,
            verify=False,  # 某些教育網站 SSL 憑證可能有問題
            allow_redirects=True,
        )
        response.raise_for_status()

        # 檢查檔案大小
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            return None, f"檔案過大（超過 {MAX_FILE_SIZE // (1024*1024)}MB）"

        pdf_bytes = response.content

        if len(pdf_bytes) < 100:
            return None, "下載的檔案太小，可能不是有效的 PDF"

        # 驗證是否為 PDF
        if not pdf_bytes[:5] == b"%PDF-":
            # 嘗試跳過 BOM 或前導空白
            stripped = pdf_bytes.lstrip()
            if not stripped[:5] == b"%PDF-":
                return None, "下載的檔案不是有效的 PDF 格式"
            pdf_bytes = stripped

        return pdf_bytes, None

    except requests.exceptions.Timeout:
        return None, "下載逾時，請稍後再試"
    except requests.exceptions.ConnectionError:
        return None, "無法連線到伺服器，請檢查網址是否正確"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP 錯誤: {e.response.status_code}"
    except Exception as e:
        return None, f"下載失敗: {str(e)}"


def extract_text_from_pdf(
    pdf_bytes: bytes,
    remove_headers_footers: bool = True,
    remove_page_numbers: bool = True,
    remove_watermarks: bool = True,
    remove_toc: bool = True,
    min_line_length: int = 2,
) -> Tuple[Optional[str], Optional[str]]:
    """
    從 PDF 提取乾淨文字，最適合 NotebookLM 使用

    Args:
        pdf_bytes: PDF 檔案的二進位內容
        remove_headers_footers: 是否移除頁首頁尾
        remove_page_numbers: 是否移除頁碼
        remove_watermarks: 是否移除浮水印文字
        remove_toc: 是否移除目錄頁
        min_line_length: 最短行長度（過短的行通常是垃圾）

    Returns:
        (clean_text, error_message) - 成功時 error_message 為 None
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        return None, f"無法開啟 PDF 檔案: {str(e)}"

    try:
        total_pages = len(doc)
        if total_pages == 0:
            return None, "PDF 檔案沒有任何頁面"

        # 第一輪：收集所有頁面的原始文字和統計資訊
        page_texts = []
        all_lines_with_freq = {}  # 用於偵測重複的頁首頁尾

        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")
            lines = text.split("\n")
            page_texts.append(lines)

            # 統計每行出現的頻率（用於偵測頁首頁尾）
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and len(stripped) > 1:
                    key = stripped[:50]  # 取前50字作為 key
                    if key not in all_lines_with_freq:
                        all_lines_with_freq[key] = {"count": 0, "positions": []}
                    all_lines_with_freq[key]["count"] += 1
                    # 記錄是在頁面的上方還是下方
                    relative_pos = i / max(len(lines), 1)
                    all_lines_with_freq[key]["positions"].append(relative_pos)

        # 找出可能的頁首頁尾文字（出現在超過 50% 頁面且位置固定的文字）
        header_footer_patterns = set()
        if remove_headers_footers and total_pages > 2:
            threshold = max(3, total_pages * 0.4)
            for key, info in all_lines_with_freq.items():
                if info["count"] >= threshold:
                    positions = info["positions"]
                    # 檢查是否都在頁面頂部或底部
                    avg_pos = sum(positions) / len(positions)
                    if avg_pos < 0.15 or avg_pos > 0.85:
                        header_footer_patterns.add(key)

        # 第二輪：清理每頁文字
        cleaned_pages = []
        toc_ended = False

        for page_num, lines in enumerate(page_texts):
            # 偵測目錄頁（通常在前幾頁，包含大量 "..." 或頁碼引用）
            if remove_toc and not toc_ended and page_num < min(10, total_pages // 3):
                toc_indicators = sum(
                    1
                    for line in lines
                    if re.search(r"\.{3,}|\…{2,}", line)
                    or re.match(r"^\s*第[一二三四五六七八九十\d]+[章節單元課]", line.strip())
                    and re.search(r"\d+\s*$", line.strip())
                )
                if toc_indicators > len(lines) * 0.3 and toc_indicators > 3:
                    continue  # 跳過目錄頁
                elif page_num > 0:
                    toc_ended = True

            cleaned_lines = []
            for i, line in enumerate(lines):
                stripped = line.strip()

                # 跳過空行
                if not stripped:
                    if cleaned_lines and cleaned_lines[-1] != "":
                        cleaned_lines.append("")  # 保留段落間的空行
                    continue

                # 移除頁碼
                if remove_page_numbers and is_page_number(stripped, page_num + 1, total_pages):
                    continue

                # 移除頁首頁尾
                if remove_headers_footers and stripped[:50] in header_footer_patterns:
                    continue

                # 移除浮水印文字
                if remove_watermarks and is_watermark(stripped):
                    continue

                # 移除過短的行（通常是垃圾）
                if len(stripped) < min_line_length:
                    continue

                # 移除純裝飾線
                if re.match(r"^[-=_─━═▬▭▮▯◻◼◽◾]+$", stripped):
                    continue

                cleaned_lines.append(stripped)

            # 移除頁面開頭和結尾的空行
            while cleaned_lines and cleaned_lines[0] == "":
                cleaned_lines.pop(0)
            while cleaned_lines and cleaned_lines[-1] == "":
                cleaned_lines.pop()

            if cleaned_lines:
                cleaned_pages.append("\n".join(cleaned_lines))

        doc.close()

        if not cleaned_pages:
            return None, "PDF 中沒有可提取的文字內容（可能是掃描圖片型 PDF）"

        # 合併所有頁面，用雙換行分隔
        full_text = "\n\n".join(cleaned_pages)

        # 最終清理
        full_text = final_cleanup(full_text)

        if len(full_text.strip()) < 10:
            return None, "提取的文字內容過少，可能是掃描圖片型 PDF"

        return full_text, None

    except Exception as e:
        doc.close()
        return None, f"文字提取失敗: {str(e)}"


def is_page_number(text: str, current_page: int, total_pages: int) -> bool:
    """判斷文字是否為頁碼"""
    text = text.strip()

    # 純數字頁碼
    if re.match(r"^\d{1,4}$", text):
        try:
            num = int(text)
            if 0 < num <= total_pages + 10:
                return True
        except ValueError:
            pass

    # 常見頁碼格式
    page_patterns = [
        r"^第?\s*\d+\s*頁$",
        r"^Page\s*\d+$",
        r"^-\s*\d+\s*-$",
        r"^\d+\s*/\s*\d+$",
        r"^P\.\s*\d+$",
        r"^p\.\s*\d+$",
        r"^\(\s*\d+\s*\)$",
        r"^【\s*\d+\s*】$",
    ]

    for pattern in page_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    return False


def is_watermark(text: str) -> bool:
    """判斷文字是否為浮水印"""
    text = text.strip().lower()
    watermark_keywords = [
        "confidential",
        "draft",
        "sample",
        "watermark",
        "浮水印",
        "草稿",
        "僅供參考",
        "請勿外流",
        "版權所有",
        "翻印必究",
    ]
    # 浮水印通常是重複的短文字
    if len(text) < 20 and any(kw in text for kw in watermark_keywords):
        return True
    return False


def final_cleanup(text: str) -> str:
    """最終文字清理"""
    # 移除連續多個空行（保留最多兩個換行）
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 移除行首行尾多餘空白
    lines = text.split("\n")
    lines = [line.strip() for line in lines]
    text = "\n".join(lines)

    # 合併被斷行的段落（中文段落中間不應有換行）
    # 如果上一行不是以標點結尾且下一行不是以特殊字元開頭，嘗試合併
    merged_lines = []
    for line in lines:
        if (
            merged_lines
            and merged_lines[-1]
            and line
            and not re.match(r"^[#\-\*\d\(（【「『《〈]", line)
            and not re.search(r"[。！？；：\.\!\?\;\:]$", merged_lines[-1])
            and not merged_lines[-1].endswith("：")
            and len(merged_lines[-1]) > 5
            and len(line) > 5
            # 只合併看起來像是同一段落的行
            and not line.startswith(" ")
        ):
            # 檢查是否為中文段落的斷行
            if re.search(r"[\u4e00-\u9fff]$", merged_lines[-1]) and re.match(
                r"^[\u4e00-\u9fff]", line
            ):
                merged_lines[-1] += line
                continue

        merged_lines.append(line)

    text = "\n".join(merged_lines)

    # 最終移除多餘空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def generate_filename(title: str, suffix: str = "txt") -> str:
    """
    根據標題生成適當的檔案名稱

    Args:
        title: PDF 標題
        suffix: 檔案副檔名

    Returns:
        格式化的檔案名稱，例如 國一數學_先修講義_20260406.txt
    """
    # 清理標題
    clean = re.sub(r"[^\w\u4e00-\u9fff\-]", "_", title)
    clean = re.sub(r"_+", "_", clean).strip("_")

    # 限制長度
    if len(clean) > 40:
        clean = clean[:40]

    # 加上日期
    date_str = datetime.now().strftime("%Y%m%d")

    return f"{clean}_{date_str}.{suffix}"


def get_pdf_info(pdf_bytes: bytes) -> dict:
    """取得 PDF 基本資訊"""
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        info = {
            "pages": len(doc),
            "metadata": doc.metadata,
            "file_size": len(pdf_bytes),
            "file_size_str": format_file_size(len(pdf_bytes)),
        }
        doc.close()
        return info
    except Exception:
        return {
            "pages": 0,
            "metadata": {},
            "file_size": len(pdf_bytes),
            "file_size_str": format_file_size(len(pdf_bytes)),
        }


def format_file_size(size_bytes: int) -> str:
    """格式化檔案大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
