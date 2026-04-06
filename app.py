"""
均一教育平台影片搜尋 & NotebookLM 一鍵匯入助手
====================================================
"""

import os
import sys
import base64
import logging
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.search_engine import (
    search_edu_pdfs,
    SEARCH_EXAMPLES,
    HOT_SEARCHES,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="均一教育影片助手 | NotebookLM 匯入",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    :root {
        --primary: #8dc63f; /* Junyi Green */
        --success: #0d9488;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg-light: #f8fafc;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main-header {
        background: linear-gradient(135deg, #8dc63f 0%, #689f38 100%);
        color: white;
        padding: 2rem 2rem 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(141, 198, 63, 0.3);
    }
    .main-header h1 {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    .main-header p {
        font-size: 1.05rem;
        opacity: 0.92;
        margin: 0;
    }
    .result-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .result-card:hover {
        border-color: #8dc63f;
        box-shadow: 0 4px 12px rgba(141, 198, 63, 0.15);
        transform: translateY(-1px);
    }
    .result-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #33691e;
        margin-bottom: 0.4rem;
        line-height: 1.4;
    }
    .result-snippet {
        color: #64748b;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-bottom: 0.5rem;
    }
    .result-source {
        display: inline-block;
        background: #f1f8e9;
        color: #558b2f;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .stats-bar {
        background: #f1f8e9;
        border: 1px solid #c5e1a5;
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .tip-box {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border: 1px solid #6ee7b7;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
    .custom-footer {
        text-align: center;
        padding: 1.5rem;
        margin-top: 3rem;
        border-top: 1px solid #e2e8f0;
        color: #94a3b8;
        font-size: 0.85rem;
    }
    stProgress > div > div > div > div {
        background: linear-gradient(90deg, #8dc63f, #0d9488);
    }
    .video-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        background-color: #fff;
    }
</style>
""",
    unsafe_allow_html=True,
)

def init_session_state():
    defaults = {
        "search_results": [],
        "search_history": [],
        "current_query": "",
        "selected_videos": set(),
        "search_count": 0,
        "is_searching": False,
        "trigger_search": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

def trigger_search_cb():
    st.session_state.trigger_search = True


def add_to_history(query: str):
    if query and query not in st.session_state.search_history:
        st.session_state.search_history.insert(0, query)
        if len(st.session_state.search_history) > 20:
            st.session_state.search_history = st.session_state.search_history[:20]

st.markdown(
    """
<div class="main-header">
    <h1>🎥 均一教育平台影片搜尋 & NotebookLM 助手</h1>
    <p>搜尋 https://www.youtube.com/@JunyiAcademy 上的影片 → 收集連結 → 一鍵匯入 Google NotebookLM 開始 AI 學習</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 📦 批次操作: 匯入 NotebookLM")

if not st.session_state.selected_videos:
    st.info("💡 請先使用下方搜尋，並勾選想加入的影片，勾選的影片連結將在這邊合併！")
else:
    st.success(f"已收集 {len(st.session_state.selected_videos)} 部影片連結：")
    
    links_text = "\n".join(list(st.session_state.selected_videos))
    st.code(links_text, language="text")

    batch_cols = st.columns([1, 1, 1, 1])

    with batch_cols[0]:
        st.download_button(
            label=f"📦 下載 (*.txt)",
            data=links_text.encode("utf-8"),
            file_name=f"均一影片連結_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with batch_cols[1]:
        txt_b64 = base64.b64encode(links_text.encode("utf-8")).decode()
        batch_js_code = f"""<div style="width:100%;">
<button type="button" onclick="
    try {{
        var b64 = '{txt_b64}';
        var binString = atob(b64);
        var bytes = new Uint8Array(binString.length);
        for (var i = 0; i < binString.length; i++) {{
            bytes[i] = binString.charCodeAt(i);
        }}
        var text = new TextDecoder('utf-8').decode(bytes);
        var textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        var success = false;
        try {{
            success = document.execCommand('copy');
        }} catch(err) {{
            console.error('Copy error', err);
        }}
        document.body.removeChild(textArea);
        if (success) {{
            alert('✅ 影片連結已全數複製！請開啟 NotebookLM 貼上連結。');
        }} else {{
            alert('❌ 複製失敗，請嘗試手動複製。');
        }}
    }} catch(e) {{
        console.error(e);
        alert('操作發生預期外的錯誤！');
    }}
" style="display:inline-block; width:100%; border:none; outline:none; font-family:inherit; background:linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color:white !important; padding:0.6rem 1rem; border-radius:8px; font-size:0.95rem; font-weight:600; text-align:center; text-decoration:none; box-shadow:0 2px 8px rgba(2,132,199,0.3); cursor:pointer; transition:all 0.2s;">
📋 複製全部連結
</button>
</div>"""
        st.markdown(batch_js_code, unsafe_allow_html=True)
        
    with batch_cols[2]:
        st.link_button("🚀 開啟 NotebookLM", "https://notebooklm.google.com/", use_container_width=True)

    with batch_cols[3]:
        if st.button("🗑️ 清空清單", use_container_width=True):
            st.session_state.selected_videos.clear()
            st.rerun()

st.divider()

with st.sidebar:
    st.markdown("### 🎯 使用說明")
    st.markdown(
        """
    1. **輸入關鍵字**搜尋均一教育平台(YouTube)影片
    2. **勾選結果**，將想學習的影片加入清單
    3. **一鍵複製**影片連結
    4. **匯入** NotebookLM 取得 AI 摘要
    """
    )
    st.divider()
    st.markdown("### 📋 搜尋歷史")
    if st.session_state.search_history:
        for i, q in enumerate(st.session_state.search_history[:10]):
            if st.button(f"🔍 {q}", key=f"history_{i}", use_container_width=True):
                st.session_state.current_query = q
                st.session_state.trigger_search = True
                st.rerun()
    else:
        st.caption("尚無搜尋紀錄")

    st.divider()
    max_results = st.slider("最大搜尋結果數", 5, 100, 100, step=5)

st.markdown("### 🔍 影片搜尋")
grade_options = ["不分年級", "一年級", "二年級", "三年級", "四年級", "五年級", "六年級", "七年級", "八年級", "九年級", "十年級", "十一年級", "十二年級"]

col_grade, col_search, col_btn = st.columns([2, 4, 1])
with col_grade:
    selected_grade = st.selectbox(
        "選擇年級",
        grade_options,
        index=0,
        label_visibility="collapsed",
        on_change=trigger_search_cb,
    )
with col_search:
    search_query = st.text_input(
        "輸入搜尋關鍵字",
        value=st.session_state.current_query,
        placeholder="例如：因式分解",
        label_visibility="collapsed",
        on_change=trigger_search_cb,
    )
with col_btn:
    search_clicked = st.button("🔍 搜尋", type="primary", use_container_width=True)

strict_mode = st.checkbox("⚗️ 啟動嚴格過濾（結果必須包含輸入的年級與字詞）", value=False)

st.markdown("##### 🔥 熱門搜尋")
hot_cols = st.columns(len(HOT_SEARCHES))
for i, hot in enumerate(HOT_SEARCHES):
    with hot_cols[i]:
        if st.button(hot["label"], key=f"hot_{i}", use_container_width=True):
            st.session_state.current_query = hot["query"]
            st.session_state.trigger_search = True
            st.rerun()

with st.expander("💡 更多搜尋範例", expanded=False):
    example_cols = st.columns(4)
    for i, example in enumerate(SEARCH_EXAMPLES):
        with example_cols[i % 4]:
            if st.button(f"📎 {example}", key=f"example_{i}", use_container_width=True):
                st.session_state.current_query = example
                st.session_state.trigger_search = True
                st.rerun()

st.divider()

has_valid_query = bool(search_query.strip() or selected_grade != "不分年級")
should_search = (search_clicked or st.session_state.get("trigger_search", False)) and has_valid_query

if should_search:
    st.session_state.trigger_search = False
    
    # 組合年級條件做為紀錄與顯示用
    final_query = search_query.strip()
    if selected_grade != "不分年級":
        if selected_grade not in final_query:
            final_query = f"{selected_grade} {final_query}"
            
    st.session_state.current_query = final_query.strip()
    add_to_history(final_query.strip())
    st.session_state.search_count += 1

    with st.spinner("🔍 正在 YouTube 搜尋均一教育平台影片..."):
        results = search_edu_pdfs(
            grade=selected_grade,
            query=search_query.strip(),
            max_results=max_results,
            strict_mode=strict_mode,
        )
        st.session_state.search_results = results

if st.session_state.search_results:
    results = st.session_state.search_results
    total = len(results)

    st.markdown(
        f'''
    <div class="stats-bar">
        <span style="font-size:1.2rem;">📊</span>
        <span>找到 <strong>{total}</strong> 筆影片結果</span>
        <span style="margin-left:auto; color:#64748b; font-size:0.85rem;">
            搜尋關鍵字：{st.session_state.current_query}
        </span>
    </div>
    ''',
        unsafe_allow_html=True,
    )

    if st.button("➕ 將所有搜尋結果加入清單 (Select All)"):
        for res in results:
            st.session_state.selected_videos.add(res["url"])
        st.rerun()

    for idx, result in enumerate(results):
        title = result["title"]
        snippet = result["snippet"]
        url = result["url"]
        
        col1, col2 = st.columns([1, 10])
        with col1:
            is_selected = url in st.session_state.selected_videos
            if st.checkbox("選擇", value=is_selected, key=f"select_{idx}_{url}", label_visibility="collapsed"):
                st.session_state.selected_videos.add(url)
            else:
                if url in st.session_state.selected_videos:
                    st.session_state.selected_videos.remove(url)
        with col2:
            st.markdown(
                f'''
            <div class="result-card" style="margin-bottom: 0px; padding: 1rem;">
                <div style="display: flex; justify-content: space-between;">
                    <div style="flex:1;">
                        <a href="{url}" target="_blank" style="text-decoration: none;">
                            <div class="result-title">🎥 {title}</div>
                        </a>
                        <div class="result-snippet">{snippet[:150]}{'...' if len(snippet) > 150 else ''}</div>
                        <span class="result-source">📍 均一教育平台 (YouTube)</span>
                    </div>
                </div>
            </div>
            ''',
                unsafe_allow_html=True,
            )
        st.write("")

elif should_search:
    st.warning("⚠️ 未找到相關影片，請嘗試調整搜尋關鍵字。")

st.markdown(
    """
<div class="custom-footer">
    <p>🎥 均一教育平台影片 & NotebookLM 助手</p>
    <p>資源來自 YouTube，僅提供快速索引與匯入 NotebookLM 輔助學習用。</p>
    <p style="margin-top: 0.5rem; font-size: 0.75rem;">
        © 2026 | Powered by Streamlit + DuckDuckGo
    </p>
</div>
""",
    unsafe_allow_html=True,
)
