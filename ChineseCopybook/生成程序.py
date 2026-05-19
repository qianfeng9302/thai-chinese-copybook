import os
import re
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style

# ---------------------------------------------------------
# 配置区
# ---------------------------------------------------------
FONT_DIR = "fonts"
CHINESE_FONT = os.path.join(FONT_DIR, "chinese.ttf")
THAI_FONT = os.path.join(FONT_DIR, "thai.ttf")
INPUT_FILE = "words.txt"

# 注册字体
pdfmetrics.registerFont(TTFont('Chinese', CHINESE_FONT))
pdfmetrics.registerFont(TTFont('Thai', THAI_FONT))


class ThaiChineseCopybook:
    def __init__(self, output_name="Copybook.pdf"):
        self.c = canvas.Canvas(output_name, pagesize=A4)
        self.width, self.height = A4

        # 核心排版参数
        self.grid_size = 16 * mm  # 田字格尺寸
        self.cols_per_row = 8  # 每行8个格
        self.rows_per_page = 10  # 每页10行

        # 自动居中左边距计算 (128mm 宽)
        content_width = self.grid_size * self.cols_per_row
        self.margin_x = (self.width - content_width) / 2

        # --- 纵向空间精细微调，防止超出纸张 ---
        self.margin_y = 18 * mm  # 字帖第一行距离顶部的距离
        self.pinyin_area = 4.5 * mm  # 拼音区高度（略微压缩）
        self.thai_area = 5 * mm  # 底部综合区高度（略微压缩）
        self.row_spacing = 2 * mm  # 行与行之间的紧凑间距

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
            # 调整中文字体在压缩格子后的纵向居中位置
            self.c.drawCentredString(x + self.grid_size / 2, y + 2.5 * mm, char)

    def draw_pinyin_lines(self, x, y):
        """绘制上方拼音辅助线"""
        line_w = self.grid_size * self.cols_per_row
        self.c.setDash(1, 1)
        self.c.setLineWidth(0.2)
        h = 1.5 * mm  # 略微缩减拼音线间距
        for i in range(3):
            self.c.line(x, y + i * h, x + line_w, y + i * h)
        self.c.setDash()

    def draw_info_zone(self, x, y, pinyin_text, thai_trans):
        """绘制下方综合信息区"""
        line_w = self.grid_size * self.cols_per_row
        self.c.setLineWidth(0.5)
        self.c.setStrokeColorRGB(0, 0, 0)
        self.c.rect(x, y, line_w, self.thai_area)

        # 拼音部分 (适当调小字号至9号，使其更精致并适应高度)
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
        """在页面右上方绘制作者和时间信息（固定绝对位置，不影响字帖）"""
        self.c.setFont('Chinese', 8.5)
        self.c.setFillColorRGB(0.5, 0.5, 0.5)  # 灰色文字
        header_text = f"by: ZHENG  |  Date: {self.current_time_str}"

        right_bound = self.margin_x + (self.grid_size * self.cols_per_row)
        # 固定在距离最顶部 10mm 的位置，不参与下面的循环计算
        self.c.drawRightString(right_bound, self.height - 10 * mm, header_text)
        self.c.setFillColorRGB(0, 0, 0)  # 恢复黑色

    def get_word_pinyin(self, word):
        """获取带声调的完整拼音"""
        pinyin_list = pinyin(word, style=Style.TONE)
        return " ".join([item[0] for item in pinyin_list])

    def create(self, words):
        if not words:
            print("错误：没有识别到有效词语。")
            return

        processed_data = []
        print(f"正在获取翻译与拼音，共需处理 {len(words)} 个词...")

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

        # 第一页初始先绘制页眉
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

            # 间距递减
            y_cursor = thai_y - self.row_spacing
            row_count += 1
            print(f"已排版: {item['char']} ({item['pinyin']})")

        self.c.save()
        print(f"\n成功！字帖整体已安全收缩在 A4 纸张内。")


def load_words_from_txt(filepath):
    """读取 TXT 文件并解析词语"""
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("天气, 谢谢")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        raw_words = re.split(r'[,，\s\n；;、]+', content)
        clean_words = [w.strip() for w in raw_words if w.strip()]
        return clean_words


# --- 执行主程序 ---
if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"zitie_{timestamp}.pdf"

    words_list = load_words_from_txt(INPUT_FILE)

    if words_list:
        app = ThaiChineseCopybook(filename)
        app.create(words_list)