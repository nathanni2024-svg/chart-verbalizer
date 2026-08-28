import fitz  # PyMuPDF
import io
import json
import base64
import os
from PIL import Image
from openai import OpenAI
from google import genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor

def extract_images_from_pdf(pdf_bytes):
    """从上传的 PDF 字节流中提取所有图片（含矢量图页面渲染）"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    extracted_images = []
    
    for page_idx, page in enumerate(doc):
        # 1. 尝试提取内嵌的位图图片
        image_list = page.get_images(full=True)
        page_has_raster = False
        
        for img_idx, img_meta in enumerate(image_list):
            xref = img_meta[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            image = Image.open(io.BytesIO(image_bytes))
            if image.width > 150 and image.height > 150:
                extracted_images.append({
                    "page": page_idx + 1,
                    "index": img_idx + 1,
                    "bytes": image_bytes,
                    "format": image_ext,
                    "image_obj": image,
                    "is_full_page": False
                })
                page_has_raster = True
                
        # 2. 兜底机制：如果页面中没有内嵌位图，但页面中含有图表关键字
        if not page_has_raster:
            text = page.get_text().lower()
            if any(kw in text for kw in ["figure", "fig.", "图", "scatterplot", "bar chart", "histogram", "boxplot"]):
                # 渲染页面为高分辨率图片 (2.0 倍缩放，确保大模型能看清字)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(image_bytes))
                extracted_images.append({
                    "page": page_idx + 1,
                    "index": 1,
                    "bytes": image_bytes,
                    "format": "png",
                    "image_obj": image,
                    "is_full_page": True
                })
                
    return extracted_images

def analyze_chart_accessibility(image_bytes, is_full_page=False, language="简体中文"):
    """调用大模型（OpenAI GPT-4o 或 Google Gemini 2.5 Flash）提取学术图表的无障碍要素与数据表格"""
    api_key = os.environ.get("OPENAI_API_KEY")
    
    system_prompt = f"""You are a digital accessibility and information architecture expert. 
Please analyze the academic chart and output a JSON object in the following format (no markdown code blocks):
{{
  "alt_text": "Single-sentence description explaining the chart type and core subject (under 50 words), written in {language}.",
  "trend_summary": "Analysis of academic trends, extreme values, and key inflection points (under 150 words), written in {language}.",
  "table_headers": ["Column 1", "Column 2", ... (Headers translated or written in {language})],
  "table_rows": [
    ["Data 1", "Data 2", ...],
    ["Data 3", "Data 4", ...]
  ]
}}"""

    user_text = f"Please analyze this academic chart, extract all data, and reconstruct it into an accessible semantic structure. Output all textual descriptions and table headers in {language}."
    if is_full_page:
        user_text = f"This image is a full academic paper page containing text and figures. Please ignore the body text, locate the chart (such as a scatterplot, histogram, line graph, or boxplot), extract all of its data, and reconstruct it into an accessible semantic structure. Output all textual descriptions and table headers in {language}."

    # 判断 API Key 的类型
    is_gemini_key = api_key and (api_key.startswith("AQ.") or api_key.startswith("AIza"))
    
    if is_gemini_key:
        client = genai.Client(api_key=api_key)
        image = Image.open(io.BytesIO(image_bytes))
        
        from tenacity import retry, stop_after_attempt, wait_exponential
        
        def _call_gemini_model_with_retry(model_name):
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=2, min=2, max=10),
                reraise=True
            )
            def _inner():
                return client.models.generate_content(
                    model=model_name,
                    contents=[user_text, image],
                    config=dict(
                        system_instruction=system_prompt,
                        response_mime_type="application/json"
                    )
                )
            return _inner()
            
        try:
            # 1st attempt: Try stable gemini-flash-latest
            response = _call_gemini_model_with_retry('gemini-flash-latest')
        except Exception as e:
            try:
                # 2nd attempt (fallback): Try lighter gemini-flash-lite-latest under high load
                response = _call_gemini_model_with_retry('gemini-flash-lite-latest')
            except Exception:
                raise e
                
        return json.loads(response.text)
    else:
        client = OpenAI(api_key=api_key)
        base64_img = base64.b64encode(image_bytes).decode('utf-8')
        
        from tenacity import retry, stop_after_attempt, wait_exponential
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _call_openai_with_retry():
            return client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
                    ]}
                ]
            )
            
        response = _call_openai_with_retry()
        return json.loads(response.choices[0].message.content)

def create_accessible_docx(processed_charts):
    """构建符合无障碍规范的 Word 文档"""
    doc = Document()
    
    # 标题
    title = doc.add_heading("学术文献图表无障碍转译报告", level=1)
    
    for idx, item in enumerate(processed_charts):
        doc.add_heading(f"图表 {idx + 1}（源自 PDF 第 {item['page']} 页）", level=2)
        
        # 1. 插入图片
        img_stream = io.BytesIO(item['bytes'])
        doc.add_picture(img_stream, width=Inches(4.5))
        
        # 2. 替代文本标签
        p_alt = doc.add_paragraph()
        p_alt_run = p_alt.add_run(f"【Alt Text / 读屏替代文本】: {item['data']['alt_text']}")
        p_alt_run.font.size = Pt(9.5)
        p_alt_run.font.italic = True
        p_alt_run.font.color.rgb = RGBColor(100, 100, 100)
        
        # 3. 趋势概括
        doc.add_heading("核心数据趋势", level=3)
        doc.add_paragraph(item['data']['trend_summary'])
        
        # 4. 语义化数据表格（供 NVDA/JAWS 遍历）
        doc.add_heading("图表原始数据还原表", level=3)
        headers = item['data']['table_headers']
        rows = item['data']['table_rows']
        
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = 'Light Shading Accent 1'
        
        # 填充表头
        for col_idx, header_text in enumerate(headers):
            cell = table.cell(0, col_idx)
            cell.text = str(header_text)
            
        # 填充数据行
        for row_idx, row_data in enumerate(rows):
            for col_idx, val in enumerate(row_data):
                table.cell(row_idx + 1, col_idx).text = str(val)
                
        doc.add_paragraph() # 空行分隔
        
    output_stream = io.BytesIO()
    doc.save(output_stream)
    output_stream.seek(0)
    return output_stream
