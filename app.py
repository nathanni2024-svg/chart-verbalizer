import os
import pandas as pd
import streamlit as st
from pipeline import extract_images_from_pdf, analyze_chart_accessibility, create_accessible_docx

st.set_page_config(page_title="Chart Verbalizer", layout="wide")
st.title("📄 PDF 学术图表无障碍转译工作台")
st.caption("基于多模态大模型与语义重构技术的无障碍文档生成工具")

# API Key 配置
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and os.path.exists(".env"):
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ["OPENAI_API_KEY"] = api_key
    except Exception:
        pass

if not api_key:
    st.sidebar.warning("⚠️ 未检测到 API Key 配置")
    api_key_input = st.sidebar.text_input("请输入 OpenAI 或 Gemini API Key", type="password")
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input
        api_key = api_key_input
        if api_key.startswith("AQ.") or api_key.startswith("AIza"):
            st.sidebar.success("🔑 Gemini API Key 已临时配置")
        else:
            st.sidebar.success("🔑 OpenAI API Key 已临时配置")
    else:
        st.sidebar.info("请在左侧输入 API Key（支持 OpenAI `sk-...` 或 Gemini `AQ...`/`AIza...`），或者创建 `.env` 文件。")
else:
    if api_key.startswith("AQ.") or api_key.startswith("AIza"):
        st.sidebar.success("🔑 Gemini API Key 已成功自动加载")
    else:
        st.sidebar.success("🔑 OpenAI API Key 已成功自动加载")

uploaded_file = st.file_uploader("上传含有图表的学术 PDF", type=["pdf"])

if uploaded_file:
    if st.button("开始提取与转译"):
        if not api_key:
            st.error("请先配置 OpenAI API Key 才能进行转译。")
            st.stop()
        with st.spinner("正在解析 PDF 图像层..."):
            pdf_bytes = uploaded_file.read()
            images = extract_images_from_pdf(pdf_bytes)
            
        if not images:
            st.warning("未在该 PDF 中检测到有效分辨率的学术图表。")
        else:
            st.success(f"成功定位到 {len(images)} 张学术图表，正在进行无障碍数据重构...")
            
            processed_results = []
            progress_bar = st.progress(0)
            has_error = False
            
            for idx, img_info in enumerate(images):
                with st.spinner(f"正在分析第 {idx+1}/{len(images)} 张图表..."):
                    try:
                        parsed_data = analyze_chart_accessibility(
                            img_info['bytes'], 
                            is_full_page=img_info.get('is_full_page', False)
                        )
                        img_info['data'] = parsed_data
                        processed_results.append(img_info)
                    except Exception as e:
                        has_error = True
                        st.error(f"❌ 分析第 {idx+1} 张图表时出错。可能是您的 API Key 不正确、网络问题或额度不足。")
                        st.error(f"具体错误信息: {e}")
                        break
                progress_bar.progress((idx + 1) / len(images))
            
            if not has_error:
                st.divider()
                st.subheader("转译结果预览")
                
                # 展示预览
                for item in processed_results:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(item['bytes'], caption=f"第 {item['page']} 页图表")
                    with col2:
                        st.markdown(f"**Alt Text:** `{item['data']['alt_text']}`")
                        st.markdown(f"**趋势分析:** {item['data']['trend_summary']}")
                        try:
                            df = pd.DataFrame(
                                item['data']['table_rows'],
                                columns=item['data']['table_headers']
                            )
                            st.dataframe(df, use_container_width=True)
                        except Exception:
                            # 维度不匹配等情况的兜底显示
                            st.dataframe(item['data']['table_rows'], use_container_width=True)
                            st.write("表头: ", item['data']['table_headers'])
                
                # 生成并下载 Word
                docx_file = create_accessible_docx(processed_results)
                st.download_button(
                    label="📥 下载无障碍 Word 文档 (.docx)",
                    data=docx_file,
                    file_name="Accessible_Paper_Charts.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
