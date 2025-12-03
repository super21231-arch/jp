import streamlit as st
import google.generativeai as genai
import random
import pandas as pd
import time

# --- 1. 頁面設定 ---
st.set_page_config(page_title="AI 日語單字特訓", page_icon="🇯🇵")
st.title("🇯🇵 AI 日語單字特訓班")

# --- 2. API 設定 ---
# 嘗試從 Secrets 讀取 Key，如果沒有就提醒使用者
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ 請先在 Streamlit 設定中填入 GEMINI_API_KEY")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. 初始化 Session State (記憶體) ---
if "vocab_list" not in st.session_state:
    # 預設範例單字
    st.session_state.vocab_list = [
        {"jp": "猫", "cn": "貓"},
        {"jp": "勉強", "cn": "學習"},
        {"jp": "世界", "cn": "世界"},
    ]
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "feedback" not in st.session_state:
    st.session_state.feedback = ""

# --- 4. 側邊欄：單字管理 ---
with st.sidebar:
    st.header("📚 單字庫管理")
    
    # 分頁：手動輸入 vs AI 生成
    tab1, tab2 = st.tabs(["📝 手動輸入", "✨ AI 生成"])
    
    with tab1:
        default_text = "猫,貓\n勉強,學習\n約束,約定"
        user_input = st.text_area("請輸入單字 (格式: 日文,中文)", value=default_text, height=200)
        
        if st.button("更新單字庫 (手動)"):
            new_list = []
            try:
                lines = user_input.strip().split('\n')
                for line in lines:
                    if "," in line:
                        parts = line.split(',')
                        new_list.append({"jp": parts[0].strip(), "cn": parts[1].strip()})
                st.session_state.vocab_list = new_list
                st.success(f"已更新 {len(new_list)} 個單字！")
            except:
                st.error("格式錯誤，請確保每行都是「日文,中文」")

    with tab2:
        topic = st.text_input("輸入主題 (例如：壽司店、搭電車)")
        level = st.selectbox("難度", ["N5 (入門)", "N4 (初級)", "N3 (中級)"])
        
        if st.button("✨ 呼叫 AI 生成單字"):
            with st.spinner("AI 正在絞盡腦汁生成單字中..."):
                prompt = f"請列出 10 個關於「{topic}」的日文單字，難度為 {level}。格式嚴格要求為 CSV 格式：日文,中文。不要有標題，不要有編號，只要純文字。"
                try:
                    response = model.generate_content(prompt)
                    text_data = response.text.strip()
                    # 解析 AI 回傳的資料
                    new_list = []
                    lines = text_data.split('\n')
                    for line in lines:
                        if "," in line:
                            parts = line.split(',')
                            new_list.append({"jp": parts[0].strip(), "cn": parts[1].strip()})
                    
                    if new_list:
                        st.session_state.vocab_list = new_list
                        st.success(f"AI 幫你生成了 {len(new_list)} 個關於 {topic} 的單字！")
                    else:
                        st.error("AI 生成格式怪怪的，請再試一次。")
                except Exception as e:
                    st.error(f"發生錯誤：{e}")

    st.divider()
    st.write(f"目前單字庫數量：{len(st.session_state.vocab_list)}")
    if st.button("🚀 開始測驗"):
        # 開始新的測驗：打亂順序
        st.session_state.quiz_data = random.sample(st.session_state.vocab_list, len(st.session_state.vocab_list))
        st.session_state.quiz_active = True
        st.session_state.current_q_index = 0
        st.session_state.score = 0
        st.session_state.feedback = ""
        st.rerun()

# --- 5. 主畫面：測驗區 ---

if not st.session_state.quiz_active:
    # 閒置狀態：顯示目前單字列表
    st.info("👈 請在左側設定單字，並按下「開始測驗」")
    if st.session_state.vocab_list:
        df = pd.DataFrame(st.session_state.vocab_list)
        st.dataframe(df, use_container_width=True)
else:
    # 測驗進行中
    total_q = len(st.session_state.quiz_data)
    current_idx = st.session_state.current_q_index
    
    # 檢查是否測驗結束
    if current_idx >= total_q:
        st.balloons()
        st.success(f"測驗結束！你的得分：{st.session_state.score} / {total_q}")
        if st.button("重新開始"):
            st.session_state.quiz_active = False
            st.rerun()
    else:
        # 顯示進度條
        progress = (current_idx / total_q)
        st.progress(progress, text=f"第 {current_idx + 1} 題 / 共 {total_q} 題")
        
        # 取得當前題目
        question = st.session_state.quiz_data[current_idx]
        
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <h1 style="font-size: 60px;">{question['jp']}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        # 使用 Form 避免按 Enter 就直接重新整理
        with st.form(key='quiz_form'):
            user_ans = st.text_input("請輸入中文意思：")
            submit_btn = st.form_submit_button("送出答案")
            
        if submit_btn:
            # 判斷對錯 (簡單字串比對)
            correct_ans = question['cn']
            
            if user_ans.strip() == "":
                st.warning("請輸入答案！")
            else:
                # 這裡使用簡單的包含判斷，只要答案中有出現關鍵字就算對
                # (例如答案是"貓"，輸入"是貓"也算對)
                if user_ans in correct_ans or correct_ans in user_ans:
                    st.session_state.score += 1
                    result_msg = "✅ 正確！"
                    msg_color = "green"
                else:
                    result_msg = f"❌ 答錯了... 正解是：{correct_ans}"
                    msg_color = "red"
                
                # --- AI 家教功能 ---
                with st.spinner("AI 老師正在造句教學中..."):
                    try:
                        prompt = f"請用日文單字「{question['jp']}」（意思是：{question['cn']}）造一個生活化的日文例句，並附上中文翻譯。請簡短回應。"
                        ai_explanation = model.generate_content(prompt).text
                    except:
                        ai_explanation = "（AI 暫時休息中，無法提供例句）"

                # 儲存結果並進下一題
                st.session_state.feedback = f"""
                ### {result_msg}
                **AI 老師例句：**
                {ai_explanation}
                """
                st.session_state.current_q_index += 1
                st.rerun()

    # 顯示上一題的結果回饋
    if st.session_state.feedback:
        st.markdown("---")
        st.markdown(st.session_state.feedback)
        if current_idx < total_q: # 如果還沒結束，給一個按鈕清除回饋專心下一題
             if st.button("下一題"):
                 st.session_state.feedback = ""
                 st.rerun()
