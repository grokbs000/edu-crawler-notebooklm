"""
核心搜尋引擎模組
使用 yt-dlp 直接搜尋均一教育平台 (JunyiAcademy) 頻道中的影片
"""

import re
import json
import logging
import subprocess
import sys
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 預設搜尋範例
# 預設搜尋範例
SEARCH_EXAMPLES = [
    "因式分解",
    "牛頓運動定律",
    "一次方程式",
    "二次函數",
]

# 熱門推薦搜尋 (快捷字串)
HOT_SEARCHES = [
    {"label": "📐 數學", "query": "數學"},
    {"label": "🔤 英文", "query": "英文"},
    {"label": "📖 國語", "query": "國語"},
    {"label": "🌍 社會", "query": "社會"},
    {"label": "🌱 自然", "query": "自然"},
    {"label": "🌎 地科", "query": "地科"},
    {"label": "🧪 理化", "query": "理化"}
]

import urllib.parse

def search_edu_pdfs(
    grade: str,
    query: str,
    max_results: int = 15,
    strict_mode: bool = False
) -> List[Dict]:
    """
    依照分階段過濾的流程：
    1. YT 搜尋先聚焦在「年級」或主關鍵字上
    2. 後台再針對所有的詞進行嚴格篩選
    """
    yt_search_term = grade if (grade and grade != "不分年級") else query.strip()
    if not yt_search_term:
        yt_search_term = query.strip()

    encoded_query = urllib.parse.quote_plus(yt_search_term)
    
    # 決定過濾所需的所有關鍵字
    query_tokens = []
    if grade and grade != "不分年級":
        query_tokens.append(grade.lower())
    if query.strip():
        query_tokens.extend([q.lower() for q in query.strip().split() if q])
    
    # 只能搜尋均一教育頻道內的內容
    search_url = f"https://www.youtube.com/@JunyiAcademy/search?query={encoded_query}"
    logger.info(f"執行頻道內搜尋: {search_url}")

    # 如果要分兩階段把大量結果過濾下來，我們必須拉取更多的資料來過篩
    fetch_limit = max_results * 8 if strict_mode else max_results * 2 + 10

    command = [
        sys.executable,
        "-m", "yt_dlp",
        search_url,
        "--flat-playlist",
        "-j",
        "--playlist-end", str(fetch_limit) 
    ]
    
    all_results = []
    seen_urls = set()

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for line in process.stdout:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                
                # 判斷是否為單一影片 (過濾掉從頻道搜尋頁面抓到的 playlist)
                if data.get("ie_key") != "Youtube" and data.get("webpage_url_basename") != "watch":
                    continue
                    
                video_url = data.get("url") or data.get("webpage_url")
                if not video_url and data.get("id"):
                    video_url = f"https://www.youtube.com/watch?v={data.get('id')}"
                
                if video_url and video_url not in seen_urls:
                    seen_urls.add(video_url)
                    
                    # 取出長度、標題等
                    title = data.get("title", "未知標題")
                    snippet = data.get("description", "")
                    if not snippet:
                        snippet = "出自：均一教育平台"
                        
                    if strict_mode and query_tokens:
                        search_text = (title + " " + snippet).lower()
                        if not all(token in search_text for token in query_tokens):
                            continue
                            
                    all_results.append({
                        "title": clean_title(title),
                        "snippet": snippet,
                        "url": video_url,
                        "source": "均一教育平台 (YouTube)"
                    })
                    
                    if len(all_results) >= max_results:
                        process.terminate()
                        break
                        
            except json.JSONDecodeError:
                pass
                
    except Exception as e:
        logger.warning(f"yt-dlp 頻道內搜尋失敗: {e}")

    return all_results

def clean_title(title: str) -> str:
    """清理標題文字"""
    title = re.sub(r"\s+", " ", title).strip()
    return title if title else "未知標題"
