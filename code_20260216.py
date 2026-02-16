import qrcode
from qrcode.constants import ERROR_CORRECT_L
from PIL import Image
import py7zr
import cv2
import numpy as np
import os

# ===================== 核心配置 =====================
CANVAS_W = 1850
CANVAS_H = 1000
QR_VER = 10          # 固定Ver10
BOX_SIZE = 3         # 投屏安全最小模块
BORDER = 4           # 必须静区
ERROR_L = ERROR_CORRECT_L
DISPLAY_SEC = 2       # 每张图显示秒数

# Ver10 L级 8-bit二进制最大容量（字节）
QR_MAX_BYTES = 3706
# 数据头：序号(4B) + 总片数(4B)
HEADER_LEN = 8
DATA_PER_QR = QR_MAX_BYTES - HEADER_LEN  # 单码有效数据

# 单张画布二维码数量：5行×9列=45个
QR_PER_IMAGE = 45
ROWS = 5
COLS = 9

# ===================== 1. 文件→最高压缩7z字节流 =====================
def file_to_7z_bytes(file_path):
    print(f"正在压缩文件：{file_path}（最高压缩比）")
    with py7zr.SevenZipFile(
        mode='w',
        compression_level=9,  # 最高压缩
        password=None
    ) as archive:
        archive.write(file_path, arcname=os.path.basename(file_path))
    return archive.readall()

# ===================== 2. 生成单个二维码 =====================
def make_qr(data_bytes):
    qr = qrcode.QRCode(
        version=QR_VER,
        error_correction=ERROR_L,
        box_size=BOX_SIZE,
        border=BORDER
    )
    qr.add_data(data_bytes)
    qr.make(fit=True)
    return qr.make_image('black', 'white')

# ===================== 3. 生成一张1850×1000二维码矩阵 =====================
def make_canvas(qr_images):
    qr_w, qr_h = qr_images[0].size
    canvas = Image.new('RGB', (CANVAS_W, CANVAS_H), 'white')
    for idx, img in enumerate(qr_images):
        row = idx // COLS
        col = idx % COLS
        x = col * qr_w
        y = row * qr_h
        canvas.paste(img, (x, y))
    return canvas

# ===================== 4. 主发送逻辑 =====================
def send_file(file_path):
    if not os.path.exists(file_path):
        print("文件不存在！")
        return

    # 1. 压缩成7z字节
    file_bytes = file_to_7z_bytes(file_path)

    # 2. 数据分片
    chunks = [
        file_bytes[i:i+DATA_PER_QR]
        for i in range(0, len(file_bytes), DATA_PER_QR)
    ]
    total_chunks = len(chunks)
    total_images = (total_chunks + QR_PER_IMAGE - 1) // QR_PER_IMAGE

    print(f"压缩后总长度：{len(file_bytes)} 字节")
    print(f"总分片数：{total_chunks}，总画布数：{total_images}")

    # 3. 逐张生成、显示
    for img_idx in range(total_images):
        print(f"\n正在生成第 {img_idx+1}/{total_images} 张画布")
        current_qrs = []

        for qr_idx_in_img in range(QR_PER_IMAGE):
            chunk_idx = img_idx * QR_PER_IMAGE + qr_idx_in_img
            if chunk_idx >= total_chunks:
                break

            # 构造数据：序号(4B) + 总片数(4B) + 数据
            seq = chunk_idx.to_bytes(4, 'big', signed=False)
            total = total_chunks.to_bytes(4, 'big', signed=False)
            payload = seq + total + chunks[chunk_idx]

            qr_img = make_qr(payload)
            current_qrs.append(qr_img)

        # 生成画布并显示
        canvas = make_canvas(current_qrs)
        canvas_cv = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)

        cv2.namedWindow("QR Sender", cv2.WINDOW_NORMAL)
        cv2.imshow("QR Sender", canvas_cv)
        print(f"显示 {DISPLAY_SEC} 秒，请采集...")
        cv2.waitKey(DISPLAY_SEC * 1000)

    cv2.destroyAllWindows()
    print("\n✅ 所有画面发送完成！")

if __name__ == "__main__":
    send_file("test_file.bin")  # 把这里改成你要发送的文件
