# 🍄 Phân loại nấm — Train model & Web App (socket)

Repo gồm 2 phần chính:

1. **Huấn luyện mô hình** trong `main.ipynb` → xuất `mushroom_pipeline.joblib`  
2. **Web App thuần socket** trong `Phan-loai-nam/` → tải CSV, dự đoán, thống kê & tải kết quả

> Mục tiêu: phân loại **nấm độc** (*poisonous*) và **nấm không độc** (*edible*).

---

## 📁 Cấu trúc thư mục

```
.
├─ Dataset/
│  ├─ train.csv
│  └─ test.csv
├─ Phan-loai-nam/
│  ├─ templates/
│  │  ├─ index.html        # Trang chủ: upload + theme + giới thiệu + gallery
│  │  └─ result.html       # Kết quả: thống kê, biểu đồ, bảng ID, tải CSV
│  ├─ main.py              # Web app thuần socket (server)
│  ├─ mushroom_pipeline.joblib   # Model đã train (web app sử dụng)
│  └─ requirements.txt     # Thư viện cho web app
├─ main.ipynb              # Notebook train & đánh giá model
├─ requirements.txt        # (tuỳ chọn) Thư viện chung cho notebook
└─ README.md
```

---

## 🚀 Cài đặt nhanh

```bash
# 1) Tạo venv (khuyến nghị Python ≥ 3.9)
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 2) Cài thư viện cho notebook (và/hoặc chung)
pip install -r requirements.txt

# 3) Cài thư viện cho web app
pip install -r Phan-loai-nam/requirements.txt
```

> Bạn có thể gộp 2 file `requirements.txt` nếu muốn (cài một lần ở gốc repo).

---

# 1) `main.ipynb` — Huấn luyện mô hình

## 🧾 Giới thiệu
Notebook dùng **scikit-learn** để huấn luyện mô hình phân loại nhị phân. Mô hình được đóng gói **Pipeline** để inference trực tiếp từ CSV “thô”, sau đó lưu thành `mushroom_pipeline.joblib`.

## 🕹️ Hướng dẫn sử dụng

1. Mở `main.ipynb` trong Jupyter/VS Code.  
2. Chạy tuần tự các cell:
   - Đọc dữ liệu `Dataset/train.csv`, `Dataset/test.csv`
   - Tiền xử lý **bằng Pipeline** (OneHotEncoder/Imputer/Scaler… nếu cần)
   - Huấn luyện & đánh giá (accuracy, confusion matrix, classification report)
   - **Lưu model** về thư mục web app:
     ```python
     import joblib
     joblib.dump(pipeline, "Phan-loai-nam/mushroom_pipeline.joblib")
     ```
3. Xác nhận file `.joblib` đã nằm trong `Phan-loai-nam/`.

## 🧠 Mô tả chi tiết

- **Pipeline đầy đủ**: đưa *toàn bộ* bước biến đổi vào `sklearn.Pipeline` (ví dụ: OneHotEncoder cho cột phân loại).  
- **Nhãn**: thường dùng `p` (*poisonous*) và `e` (*edible*) hoặc 1/0; giữ nhất quán xuyên suốt.  
- **Cột ID**: nên có `id` (hoặc `*_id`) để web app hiển thị danh sách ID theo dự đoán.

## ⚠️ Lưu ý

- **BẮT BUỘC** xuất model là **Pipeline**. Nếu bạn `get_dummies()` bên ngoài rồi mới fit, khi dự đoán web app sẽ báo **thiếu cột**.  
- Tên & kiểu cột của CSV inference phải khớp với dữ liệu train.  
- Dự án mang tính học thuật/demo — **không dùng cho quyết định an toàn thực phẩm**.

---

# 2) Web App (socket) — `Phan-loai-nam/`

## 🧾 Giới thiệu
Ứng dụng web thuần **socket** (không Flask/Django). Cho phép:
- Upload **CSV** → dự đoán bằng `mushroom_pipeline.joblib`
- **Thống kê** + **2 biểu đồ** (cột & tròn – Chart.js)
- **Bảng ID** có **tìm kiếm, sắp xếp, phân trang**
- Tải **CSV kết quả** và tải riêng **ID nấm độc / không độc**
- **Theme** & **color picker** (lưu trong `localStorage`)

## 🕹️ Cách chạy

```bash
cd Phan-loai-nam
python main.py
# mở trình duyệt: http://127.0.0.1:8000
```

> `main.py` đọc model từ biến `MODEL_PATH` (mặc định: `mushroom_pipeline.joblib` đặt cùng thư mục).

## 🔧 Đầu vào CSV

- Khuyến nghị có cột **`id`** để liệt kê danh sách.  
- Nếu có cột **`class`** (nhãn thật) thì web app **bỏ qua** khi dự đoán.  
- Các cột đặc trưng phải khớp với lúc huấn luyện (tên & kiểu).  
- Ví dụ mini:

```csv
id,cap-shape,cap-surface,cap-color,odor,bruises,...
7345,x,s,n,a,t,...
6239,b,y,w,l,f,...
```

## 🧩 Thành phần chính

- **`main.py`**
  - `GET /` → trả `templates/index.html`
  - `POST /predict` → đọc CSV, dự đoán, render `templates/result.html`
  - Tự phát hiện cột ID; chọn feature theo `model.feature_names_in_` (nếu có)
  - Trả về:
    - Bảng đếm nhãn gốc & nhãn tiếng Việt
    - Hai biểu đồ (Bar & Pie)
    - **Bảng ID** (tìm kiếm/sắp xếp/phân trang)
    - File kết quả `mushroom_predictions.csv` (data URI)
    - Nút tải **ID nấm độc** & **ID nấm không độc** riêng
    - **Toast** lỗi khi CSV/model không hợp lệ

- **`templates/index.html`**  
  Trang chủ: form upload + giới thiệu + tính năng + cách dùng + gallery + **chọn theme**.

- **`templates/result.html`**  
  Trang kết quả: thống kê → **2 biểu đồ** đặt cạnh nhau, bảng ID nâng cao, tải file.

## ⚠️ Lưu ý khi dùng web app

- App mang tính **demo**: không có auth, giới hạn upload, hay hardening bảo mật.  
  Nếu triển khai thực tế, cân nhắc **FastAPI**/**Uvicorn**, reverse proxy, logging, giới hạn kích thước tệp…
- Nếu gặp lỗi **“Thiếu các cột đặc trưng mà model mong đợi”**:
  - Kiểm tra model đã là **Pipeline đầy đủ**.
  - Kiểm tra **`feature_names_in_`** khớp cột CSV.

---

## 🧪 Mở rộng (tuỳ chọn)

- Tính **accuracy/precision/recall** nếu CSV có nhãn `class`.  
- Hiển thị **feature importance/SHAP**.  
- Đóng gói **Docker** hoặc chuyển sang **FastAPI** cho production.  
- Quản lý **nhiều phiên bản model** & ghi log dự đoán.

---

## 📜 Giấy phép

Chọn license phù hợp (ví dụ **MIT**), thêm tệp `LICENSE` ở gốc repo.

---

## 🤝 Đóng góp

PR/Issue hoan nghênh: thêm API JSON `/api/predict`, virtual scroll cho bảng cực lớn, kiểm thử (pytest), CI, v.v.

---

> Gợi ý: thêm ảnh minh hoạ vào `docs/` rồi nhúng:
> 
> ```md
> ![Trang chủ](docs/screenshot-index.png)
> ![Kết quả](docs/screenshot-result.png)
> ```

---
## 👥 Nhóm thực hiện
- **Phạm Đức Duy Tiến**  
- **Dương Văn Việt**  
- **Vương Đức Tuấn**
