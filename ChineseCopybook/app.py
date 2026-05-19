import os
import re
import io
from datetime import datetime
import streamlit as st

# 引入 reportlab 核心库
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# 引入本地翻译和拼音插件
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style

# ---------------------------------------------------------
# 1. 字体配置与页面基础设置
# ---------------------------------------------------------
FONT_DIR = "fonts"
CHINESE_FONT = os.path.join(FONT_DIR, "chinese.TTF")
THAI_FONT = os.path.join(FONT_DIR, "thai.TTF")

# 设置网页标签页和样式
st.set_page_config(page_title="汉字字帖生成器", page_icon="📝", layout="centered")

# 检查本地是否有字体，线上部署时如果没有字体会抛出友好提示
if not os.path.exists(CHINESE_FONT) or not os.path.exists(THAI_FONT):
    st.error("⚠️ 未在 'fonts/' 文件夹下找到 chinese.ttf 或 thai.ttf 字体文件，请确保它们已打包上传！")
    st.stop()

# 注册字体
pdfmetrics.registerFont(TTFont('Chinese', CHINESE_FONT))
pdfmetrics.registerFont(TTFont('Thai', THAI_FONT))


# ---------------------------------------------------------
# 2. 字帖 PDF 生成核心类 (内存优化纯净版)
# ---------------------------------------------------------
class ThaiChineseCopybook:
    def __init__(self, buffer):
        # 【核心改写】直接接收内存缓冲区 buffer，不再接收文件名 filename
        self.c = canvas.Canvas(buffer, pagesize=A4)
        self.width, self.height = A4

        # 核心排版参数
        self.grid_size = 16 * mm  # 田字格尺寸
        self.cols_per_row = 8  # 每行8个格
        self.rows_per_page = 10  # 每页10行

        # 自动居中左边距计算 (128mm 宽)
        content_width = self.grid_size * self.cols_per_row
        self.margin_x = (self.width - content_width) / 2

        # 纵向空间精细微调 (遵循用户最舒适的 18mm 设定)
        self.margin_y = 18 * mm
        self.pinyin_area = 4.5 * mm
        self.thai_area = 5 * mm
        self.row_spacing = 2 * mm

        self.translator = GoogleTranslator(source='zh-CN', target='th')
        self.current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    def draw_grid(self, x, y, char="", is_template=False):
        """绘制田字格"""
        self.c.setLineWidth(0.8)
        self.c.setStrokeColorRGB(0, 0, 0)
        self.c.rect(x, y, self.grid_size, self.grid_size)

        self.c.setDash(2, 2)
        self.c.setLineWidth(0.3)
        self.c.line(x + self.grid_size / 2, y, x + self.grid_size / 2, y + self.grid_size)
        self.c.line(x, y + self.grid_size / 2, x + self.grid_size, y + self.grid_size / 2)
        self.c.setDash()

        if is_template and char:
            self.c.setFont('Chinese', 34)
            self.c.drawCentredString(x + self.grid_size / 2, y + 2.5 * mm, char)

    def draw_pinyin_lines(self, x, y):
        """绘制上方拼音辅助线"""
        line_w = self.grid_size * self.cols_per_row
        self.c.setDash(1, 1)
        self.c.setLineWidth(0.2)
        h = 1.5 * mm
        for i in range(3):
            self.c.line(x, y + i * h, x + line_w, y + i * h)
        self.c.setDash()

    def draw_info_zone(self, x, y, pinyin_text, thai_trans):
        """绘制下方综合信息区（拼音 + 泰语翻译）"""
        line_w = self.grid_size * self.cols_per_row
        self.c.setLineWidth(0.5)
        self.c.setStrokeColorRGB(0, 0, 0)
        self.c.rect(x, y, line_w, self.thai_area)

        # 拼音部分
        self.c.setFont('Chinese', 9)
        pinyin_part = f"{pinyin_text}   |   "
        self.c.drawString(x + 2 * mm, y + 1.2 * mm, pinyin_part)

        # 动态计算拼音宽度
        pinyin_width = self.c.stringWidth(pinyin_part, 'Chinese', 9)

        # 泰语部分
        self.c.setFont('Thai', 10)
        thai_part = f"แปล: {thai_trans}"
        self.c.drawString(x + 2 * mm + pinyin_width, y + 1.2 * mm, thai_part)

    def draw_header(self):
        """在页面右上方绘制作者和时间信息"""
        self.c.setFont('Chinese', 8.5)
        self.c.setFillColorRGB(0.5, 0.5, 0.5)
        header_text = f"by: ZHENG  |  Date: {self.current_time_str}"

        right_bound = self.margin_x + (self.grid_size * self.cols_per_row)
        self.c.drawRightString(right_bound, self.height - 10 * mm, header_text)
        self.c.setFillColorRGB(0, 0, 0)

    def get_word_pinyin(self, word):
        """获取带声调的完整拼音"""
        pinyin_list = pinyin(word, style=Style.TONE)
        return " ".join([item[0] for item in pinyin_list])

    def create(self, words):
        processed_data = []

        for word in words:
            try:
                thai_trans = self.translator.translate(word)
            except:
                thai_trans = "---"

            word_pinyin = self.get_word_pinyin(word)

            for char in word:
                processed_data.append({
                    "char": char,
                    "pinyin": word_pinyin,
                    "trans": thai_trans
                })

        y_cursor = self.height - self.margin_y
        row_count = 0

        self.draw_header()

        for item in processed_data:
            if row_count >= self.rows_per_page:
                self.c.showPage()
                self.draw_header()
                y_cursor = self.height - self.margin_y
                row_count = 0

            # 1. 拼音行
            pinyin_y = y_cursor - self.pinyin_area
            self.draw_pinyin_lines(self.margin_x, pinyin_y)

            # 2. 田字格行
            grid_y = pinyin_y - self.grid_size
            for col in range(self.cols_per_row):
                is_tmpl = (col == 0)
                self.draw_grid(self.margin_x + col * self.grid_size, grid_y, item['char'], is_tmpl)

            # 3. 泰语翻译行
            thai_y = grid_y - self.thai_area
            self.draw_info_zone(self.margin_x, thai_y, item['pinyin'], item['trans'])

            y_cursor = thai_y - self.row_spacing
            row_count += 1

        self.c.save()


# ---------------------------------------------------------
# 3. Streamlit 网页交互界面
# ---------------------------------------------------------
st.title("📝 泰中双语字帖自动生成器")
st.markdown("##### 专为泰国学生练习中文汉字设计（无注音纯净版）")
st.write("在下方输入你想让学生练习的中文词组，点击生成后即可下载直接打印的标准 A4 PDF 稿。")

# 文本输入区域（替代原先的 words.txt）
user_input = st.text_area(
    label="请输入词汇列表（支持换行、空格、中英文逗号、顿号或分号分隔）：",
    value="今天, 我, 去, 北京, 老师, 学生, 谢谢",
    height=150
)

# 提交按钮
if st.button("✨ 一键生成 A4 字帖 PDF", type="primary"):
    # 解析文本输入
    raw_words = re.split(r'[,，\s\n；;、]+', user_input)
    words_list = [w.strip() for w in raw_words if w.strip()]

    if not words_list:
        st.warning("⚠️ 请输入至少一个有效的中文词汇！")
    else:
        # 使用进度条增强网页交互体验
        with st.spinner("🔄 正在联网翻译并自动排版中，请稍候..."):
            # 【核心优化】创建一个内存字节流容器
            pdf_buffer = io.BytesIO()

            # 初始化字帖生成器，将 PDF 直接绘制在内存里
            app = ThaiChineseCopybook(pdf_buffer)
            app.create(words_list)

            # 把内存游标移到最开始，方便浏览器读取
            pdf_buffer.seek(0)

            # 动态生成符合你要求的日期时间文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_filename = f"Copybook_{timestamp}.pdf"

            st.success("🎉 字帖生成成功！请点击下方按钮下载。")

            # 渲染 Streamlit 自带的下载按钮
            st.download_button(
                label="📥 下载您的 A4 字帖 PDF 文件",
                data=pdf_buffer,
                file_name=download_filename,
                mime="application/pdf",
                use_container_width=True
            )
