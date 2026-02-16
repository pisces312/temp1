from pyzbar.pyzbar import decode
from PIL import Image
import cv2
import py7zr
import os
import tempfile

# ===================== 配置 =====================
received_chunks = {}  # 序号 → 数据
total_chunks = None  # 从二维码头读取

# ===================== 解析二维码数据 =====================
def parse_payload(data_bytes):
    if len(data_bytes) < 8:
        return None, None, None
    seq = int.from_bytes(data_bytes[0:4], 'big', signed=False)
    total = int.from_bytes(data_bytes[4:8], 'big', signed=False)
    payload = data_bytes[8:]
    return seq, total, payload

# ===================== 收齐后拼接+解压 =====================
def assemble_and_extract():
    global received_chunks, total_chunks

    if len(received_chunks) != total_chunks:
        return False

    print("\n✅ 已收齐所有分片，开始拼接...")
    full_data = b''
    for i in sorted(received_chunks.keys()):
        full_data += received_chunks[i]

    # 写入临时7z文件
    with tempfile.NamedTemporaryFile(suffix='.7z', delete=False) as f:
        f.write(full_data)
        tmp_7z = f.name

    # 解压
    out_dir = "./qr_receive_output"
    os.makedirs(out_dir, exist_ok=True)
    with py7zr.SevenZipFile(tmp_7z, 'r') as archive:
        archive.extractall(out_dir)

    print(f"✅ 解压完成！文件保存在：{out_dir}")
    os.unlink(tmp_7z)
    return True

# ===================== 主接收逻辑 =====================
def receive_loop():
    global total_chunks, received_chunks
    cap = cv2.VideoCapture(0)  # 0=默认摄像头（视频直采）
    print("🔍 等待二维码... 按 Q 退出")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 解码
        for code in decode(frame):
            data = code.data
            seq, total, payload = parse_payload(data)
            if seq is None:
                continue

            # 第一次获取总分片数
            if total_chunks is None:
                total_chunks = total
                print(f"\n识别到总分片数：{total_chunks}")

            # 去重：已接收的不再处理
            if seq in received_chunks:
                continue

            # 缓存
            received_chunks[seq] = payload
            print(f"接收成功：序号 {seq+1}/{total_chunks}")

            # 检查是否收齐
            if assemble_and_extract():
                break

        # 显示画面
        cv2.imshow("QR Receiver", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    receive_loop()
