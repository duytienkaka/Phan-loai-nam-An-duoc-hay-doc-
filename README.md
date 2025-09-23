# Phân loại nấm: Ăn được hay độc? 🍄

## 📌 Giới thiệu
Dự án này sử dụng **Machine Learning** để phân loại nấm dựa trên đặc trưng (màu sắc, hình dáng, mùi, …).  
Mục tiêu: Xây dựng một mô hình có thể dự đoán **nấm ăn được** hay **nấm độc**, từ đó hỗ trợ người dùng trong việc nhận diện.

Bài tập nằm trong phạm vi học tập và nghiên cứu, không được sử dụng trực tiếp để nhận diện nấm ngoài thực tế.  

---

## ⚙️ Yêu cầu hệ thống
- Python >= 3.8
- Các thư viện cần thiết được mô tả trong `requirements.txt`:
  - pandas  
  - numpy  
  - scikit-learn  
  - joblib  
  - matplotlib (nếu cần trực quan hóa)  
  - jupyter (nếu chạy notebook)

Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

---

## 📂 Cấu trúc thư mục
```
├── app/                       # Chứa code web app (FastAPI/Streamlit)
│   ├── main.py                 # File chính để chạy ứng dụng
│   ├── mushroom_pipeline.joblib # Mô hình đã huấn luyện
├── data/                      # Thư mục chứa dữ liệu (train/test)
│   ├── mushroom.csv
├── main.ipynb                 # Notebook huấn luyện và kiểm thử mô hình
├── requirements.txt           # Danh sách dependencies
├── README.md                  # Tài liệu hướng dẫn
```

---

## 🚀 Cách chạy project

### 1. Huấn luyện lại mô hình (tùy chọn)
Mở file `main.ipynb` bằng Jupyter Notebook và chạy toàn bộ cell để huấn luyện lại pipeline và lưu thành file `mushroom_pipeline.joblib`.

### 2. Chạy ứng dụng web
Ví dụ nếu dùng **FastAPI**:
```bash
cd app
uvicorn main:app --reload
```

Ứng dụng sẽ chạy tại: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 3. Upload file CSV để dự đoán
- Chuẩn bị file CSV theo định dạng mẫu hiển thị trên giao diện.  
- Upload file, ứng dụng sẽ trả về danh sách **ID nấm** cùng nhãn **ăn được / độc**.

---

## 📊 Kết quả mô hình
- Độ chính xác (Accuracy): ~95% (tùy thuộc dữ liệu huấn luyện).  
- Được kiểm thử trên tập dữ liệu [UCI Mushroom Dataset](https://archive.ics.uci.edu/ml/datasets/mushroom).

---

## 👥 Nhóm thực hiện
- **Phạm Đức Duy Tiến**  
- **Dương Văn Việt**  
- **Vương Đức Tuấn**
