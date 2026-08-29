import os
import pandas as pd
import streamlit as st
from pipeline import extract_images_from_pdf, analyze_chart_accessibility, create_accessible_docx

st.set_page_config(page_title="Chart Verbalizer", layout="wide")

# 语言选择配置 (Language Configuration placed at the top for dynamic UI translations)
language = st.sidebar.selectbox(
    "🌐 界面与输出语言 / Interface & Output Language",
    ["简体中文", "English", "Español", "日本語", "Deutsch", "Français"],
    index=0
)

# UI 语言资源包 / UI Translation Resources
UI = {
    "简体中文": {
        "title": "📄 PDF 学术图表无障碍转译工作台",
        "caption": "基于多模态大模型与语义重构技术的无障碍文档生成工具",
        "warn_no_key": "⚠️ 未检测到 API Key 配置",
        "input_key": "请输入 OpenAI 或 Gemini API Key",
        "key_temp_gemini": "🔑 Gemini API Key 已临时配置",
        "key_temp_openai": "🔑 OpenAI API Key 已临时配置",
        "key_info": "请在左侧输入 API Key（支持 OpenAI `sk-...` 或 Gemini `AQ...`/`AIza...`），或者创建 `.env` 文件。",
        "key_load_gemini": "🔑 Gemini API Key 已成功自动加载",
        "key_load_openai": "🔑 OpenAI API Key 已成功自动加载",
        "uploader_label": "上传含有图表的学术 PDF",
        "btn_start": "开始提取与转译",
        "err_no_key": "请先配置 API Key 才能进行转译。",
        "spin_pdf": "正在解析 PDF 图像层...",
        "warn_no_charts": "未在该 PDF 中检测到有效分辨率的学术图表。",
        "success_found": "成功定位到 {count} 张学术图表，正在进行无障碍数据重构...",
        "spin_chart": "正在分析第 {current}/{total} 张图表...",
        "err_analysis": "❌ 分析第 {idx} 张图表时出错。可能是您的 API Key 不正确、网络问题或额度不足。",
        "err_detail": "具体错误信息: {err}",
        "preview_header": "转译结果预览",
        "page_caption": "第 {page} 页图表",
        "trend_label": "**趋势分析:** ",
        "fallback_header": "表头: ",
        "btn_download": "📥 下载无障碍 Word 文档 (.docx)",
    },
    "English": {
        "title": "📄 PDF Academic Chart Accessibility Worktable",
        "caption": "An accessibility document compilation tool powered by Multimodal VLM and semantic reconstruction.",
        "warn_no_key": "⚠️ No API Key Configured",
        "input_key": "Enter OpenAI or Gemini API Key",
        "key_temp_gemini": "🔑 Gemini API Key configured for session",
        "key_temp_openai": "🔑 OpenAI API Key configured for session",
        "key_info": "Please enter your API Key (supports OpenAI `sk-...` or Gemini `AQ...`/`AIza...`), or create a local `.env` file.",
        "key_load_gemini": "🔑 Gemini API Key automatically loaded",
        "key_load_openai": "🔑 OpenAI API Key automatically loaded",
        "uploader_label": "Upload Academic PDF containing charts",
        "btn_start": "Start Extraction & Translation",
        "err_no_key": "Please configure your API Key before translating.",
        "spin_pdf": "Parsing PDF image layers...",
        "warn_no_charts": "No valid academic charts detected in this PDF.",
        "success_found": "Successfully located {count} academic charts. Reconstructing semantic structures...",
        "spin_chart": "Analyzing chart {current}/{total}...",
        "err_analysis": "❌ Error analyzing chart #{idx}. Please verify your API Key, network connection, or account balance.",
        "err_detail": "Error details: {err}",
        "preview_header": "Translation Results Preview",
        "page_caption": "Chart from Page {page}",
        "trend_label": "**Trend Analysis:** ",
        "fallback_header": "Headers: ",
        "btn_download": "📥 Download Accessible Word Document (.docx)",
    },
    "Español": {
        "title": "📄 Banco de Trabajo de Accesibilidad de Gráficos PDF",
        "caption": "Herramienta de generación de documentos accesible basada en modelos multimodales y reconstrucción semántica.",
        "warn_no_key": "⚠️ Clave API no configurada",
        "input_key": "Introduzca la clave API de OpenAI o Gemini",
        "key_temp_gemini": "🔑 Clave API de Gemini configurada para la sesión",
        "key_temp_openai": "🔑 Clave API de OpenAI configurada para la sesión",
        "key_info": "Por favor, introduzca su clave API (compatible con OpenAI `sk-...` o Gemini `AQ...`/`AIza...`), o cree un archivo `.env`.",
        "key_load_gemini": "🔑 Clave API de Gemini cargada automáticamente",
        "key_load_openai": "🔑 Clave API de OpenAI cargada automáticamente",
        "uploader_label": "Subir PDF académico con gráficos",
        "btn_start": "Iniciar extracción y traducción",
        "err_no_key": "Configure su clave API antes de continuar.",
        "spin_pdf": "Analizando capas de imágenes PDF...",
        "warn_no_charts": "No se detectaron gráficos válidos en este PDF.",
        "success_found": "¡Se localizaron {count} gráficos académicos! Reconstruyendo estructuras semánticas...",
        "spin_chart": "Analizando gráfico {current}/{total}...",
        "err_analysis": "❌ Error al analizar el gráfico #{idx}. Verifique su clave API, conexión de red o saldo.",
        "err_detail": "Detalles del error: {err}",
        "preview_header": "Vista previa del resultado de la traducción",
        "page_caption": "Gráfico de la página {page}",
        "trend_label": "**Análisis de tendencias:** ",
        "fallback_header": "Cabeceras: ",
        "btn_download": "📥 Descargar documento de Word accesible (.docx)",
    },
    "日本語": {
        "title": "📄 PDF学術グラフアクセシビリティ翻訳ワーク台",
        "caption": "マルチモーダル大規模モデルと意味再構築技術に基づくアクセシブルな文書作成ツール。",
        "warn_no_key": "⚠️ APIキーが設定されていません",
        "input_key": "OpenAIまたはGeminiのAPIキーを入力してください",
        "key_temp_gemini": "🔑 セッション用にGeminiのAPIキーを設定しました",
        "key_temp_openai": "🔑 セッション用にOpenAIのAPIキーを設定しました",
        "key_info": "APIキーを入力するか（OpenAI `sk-...` または Gemini `AQ...`/`AIza...` に対応）、ローカルに `.env` ファイルを作成してください。",
        "key_load_gemini": "🔑 GeminiのAPIキーが自動的に読み込まれました",
        "key_load_openai": "🔑 OpenAIのAPIキーが自動的に読み込まれました",
        "uploader_label": "グラフを含む学術PDFをアップロード",
        "btn_start": "抽出と翻訳を開始",
        "err_no_key": "翻訳を行う前にAPIキーを設定してください。",
        "spin_pdf": "PDF画像レイヤーを解析中...",
        "warn_no_charts": "このPDFで有効な解像度の学術グラフが検出されませんでした。",
        "success_found": "{count}個の学術グラフを検出しました。意味構造を再構築中...",
        "spin_chart": "グラフ {current}/{total} を分析中...",
        "err_analysis": "❌ グラフ #{idx} の分析中にエラーが発生しました。APIキー、ネットワーク接続、またはアカウント残高を確認してください。",
        "err_detail": "エラー詳細: {err}",
        "preview_header": "翻訳結果のプレビュー",
        "page_caption": "ページ {page} のグラフ",
        "trend_label": "**トレンド分析:** ",
        "fallback_header": "ヘッダー: ",
        "btn_download": "📥 アクセシブルなWord文書 (.docx) をダウンロード",
    },
    "Deutsch": {
        "title": "📄 PDF Wissenschaftliche Grafiken Barrierefreiheit-Arbeitsplatz",
        "caption": "Ein Tool zur Erstellung barrierefreier Dokumente, basierend auf multimodalen Modellen und semantischer Rekonstruktion.",
        "warn_no_key": "⚠️ Kein API-Schlüssel konfiguriert",
        "input_key": "Geben Sie den OpenAI- oder Gemini-API-Schlüssel ein",
        "key_temp_gemini": "🔑 Gemini-API-Schlüssel für Sitzung konfiguriert",
        "key_temp_openai": "🔑 OpenAI-API-Schlüssel für Sitzung konfiguriert",
        "key_info": "Bitte geben Sie Ihren API-Schlüssel ein (unterstützt OpenAI `sk-...` oder Gemini `AQ...`/`AIza...`) oder erstellen Sie eine `.env`-Datei.",
        "key_load_gemini": "🔑 Gemini-API-Schlüssel automatisch geladen",
        "key_load_openai": "🔑 OpenAI-API-Schlüssel automatisch geladen",
        "uploader_label": "Wissenschaftliches PDF mit Grafiken hochladen",
        "btn_start": "Extraktion & Übersetzung starten",
        "err_no_key": "Bitte konfigurieren Sie Ihren API-Schlüssel vor der Übersetzung.",
        "spin_pdf": "PDF-Bildebenen werden analysiert...",
        "warn_no_charts": "Keine gültigen wissenschaftlichen Grafiken in diesem PDF gefunden.",
        "success_found": "{count} wissenschaftliche Grafiken lokalisiert. Semantische Strukturen werden rekonstruiert...",
        "spin_chart": "Grafik {current}/{total} wird analysiert...",
        "err_analysis": "❌ Fehler bei der Analyse von Grafik #{idx}. Bitte überprüfen Sie Ihren API-Schlüssel, Ihre Netzwerkverbindung oder Ihr Guthaben.",
        "err_detail": "Fehlerdetails: {err}",
        "preview_header": "Vorschau der Übersetzungsergebnisse",
        "page_caption": "Grafik von Seite {page}",
        "trend_label": "**Trendanalyse:** ",
        "fallback_header": "Kopfzeilen: ",
        "btn_download": "📥 Barrierefreies Word-Dokument (.docx) herunterladen",
    },
    "Français": {
        "title": "📄 Plan de Travail d'Accessibilité des Graphiques PDF",
        "caption": "Outil de génération de documents accessibles basé sur des modèles multimodaux et la reconstruction sémantique.",
        "warn_no_key": "⚠️ Aucune clé API configurée",
        "input_key": "Entrez la clé API OpenAI ou Gemini",
        "key_temp_gemini": "🔑 Clé API Gemini configurée pour la session",
        "key_temp_openai": "🔑 Clé API OpenAI configurée pour la session",
        "key_info": "Veuillez entrer votre clé API (prend en charge OpenAI `sk-...` ou Gemini `AQ...`/`AIza...`) ou créez un fichier `.env`.",
        "key_load_gemini": "🔑 Clé API Gemini chargée automatiquement",
        "key_load_openai": "🔑 Clé API OpenAI chargée automatiquement",
        "uploader_label": "Télécharger un PDF académique contenant des graphiques",
        "btn_start": "Démarrer l'extraction et la traduction",
        "err_no_key": "Veuillez configurer votre clé API avant de traduire.",
        "spin_pdf": "Analyse des couches d'images du PDF...",
        "warn_no_charts": "Aucun graphique académique valide détecté dans ce PDF.",
        "success_found": "{count} graphiques académiques localisés. Reconstruction des structures sémantiques...",
        "spin_chart": "Analyse du graphique {current}/{total}...",
        "err_analysis": "❌ Erreur lors de l'analyse du graphique #{idx}. Veuillez vérifier votre clé API, votre connexion réseau ou votre solde.",
        "err_detail": "Détails de l'erreur: {err}",
        "preview_header": "Aperçu des résultats de la traduction",
        "page_caption": "Graphique de la page {page}",
        "trend_label": "**Analyse des tendances :** ",
        "fallback_header": "En-têtes : ",
        "btn_download": "📥 Télécharger le document Word accessible (.docx)",
    }
}

# Select UI language translation (fallback to English/default if not found)
u = UI.get(language, UI["English"])

st.title(u["title"])
st.caption(u["caption"])

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
    st.sidebar.warning(u["warn_no_key"])
    api_key_input = st.sidebar.text_input(u["input_key"], type="password")
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input
        api_key = api_key_input
        if api_key.startswith("AQ.") or api_key.startswith("AIza"):
            st.sidebar.success(u["key_temp_gemini"])
        else:
            st.sidebar.success(u["key_temp_openai"])
    else:
        st.sidebar.info(u["key_info"])
else:
    if api_key.startswith("AQ.") or api_key.startswith("AIza"):
        st.sidebar.success(u["key_load_gemini"])
    else:
        st.sidebar.success(u["key_load_openai"])

uploaded_file = st.file_uploader(u["uploader_label"], type=["pdf"])

if uploaded_file:
    import fitz
    pdf_bytes = uploaded_file.read()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
    except Exception:
        total_pages = 1
        
    start_page, end_page = 1, total_pages
    if total_pages > 1:
        label_total = f"📄 Total Pages: {total_pages}" if language != "简体中文" else f"📄 文档总页数: {total_pages}"
        label_slider = "Select Page Range to Scan" if language != "简体中文" else "选择要扫描的页码范围"
        st.info(label_total)
        page_range = st.slider(label_slider, 1, total_pages, (1, total_pages))
        start_page, end_page = page_range

    if st.button(u["btn_start"]):
        if not api_key:
            st.error(u["err_no_key"])
            st.stop()
        with st.spinner(u["spin_pdf"]):
            images = extract_images_from_pdf(pdf_bytes, start_page=start_page, end_page=end_page)
            
        if not images:
            st.warning(u["warn_no_charts"])
        else:
            st.success(u["success_found"].format(count=len(images)))
            
            processed_results = []
            progress_bar = st.progress(0)
            has_error = False
            
            for idx, img_info in enumerate(images):
                with st.spinner(u["spin_chart"].format(current=idx+1, total=len(images))):
                    try:
                        parsed_data = analyze_chart_accessibility(
                            img_info['bytes'], 
                            is_full_page=img_info.get('is_full_page', False),
                            language=language
                        )
                        img_info['data'] = parsed_data
                        processed_results.append(img_info)
                    except Exception as e:
                        has_error = True
                        st.error(u["err_analysis"].format(idx=idx+1))
                        st.error(u["err_detail"].format(err=e))
                        break
                progress_bar.progress((idx + 1) / len(images))
            
            if not has_error:
                st.divider()
                st.subheader(u["preview_header"])
                
                # 展示预览
                for item in processed_results:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(item['bytes'], caption=u["page_caption"].format(page=item['page']))
                    with col2:
                        st.markdown(f"**Alt Text:** `{item['data']['alt_text']}`")
                        st.markdown(f"{u['trend_label']}{item['data']['trend_summary']}")
                        try:
                            df = pd.DataFrame(
                                item['data']['table_rows'],
                                columns=item['data']['table_headers']
                            )
                            st.dataframe(df, use_container_width=True)
                        except Exception:
                            # 维度不匹配等情况的兜底显示
                            st.dataframe(item['data']['table_rows'], use_container_width=True)
                            st.write(u["fallback_header"], item['data']['table_headers'])
                
                # 生成并下载 Word
                docx_file = create_accessible_docx(processed_results)
                st.download_button(
                    label=u["btn_download"],
                    data=docx_file,
                    file_name="Accessible_Paper_Charts.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
