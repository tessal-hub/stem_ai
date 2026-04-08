model_path = "gesture_model.tflite"
out_path = "gesture_model.cc"

with open(model_path, "rb") as f:
    bytes_data = f.read()

with open(out_path, "w") as f:
    # alignas(8) giúp tối ưu hóa bộ nhớ cho ESP32
    f.write("alignas(8) extern const unsigned char g_model[] = {\n")
    for i, byte in enumerate(bytes_data):
        f.write(f"0x{byte:02x}, ")
        if (i + 1) % 12 == 0:
            f.write("\n")
    f.write("\n};\n")
    f.write(f"const int g_model_len = {len(bytes_data)};\n")

print(f"Thành công! Đã tạo file mảng C-array: {out_path}")