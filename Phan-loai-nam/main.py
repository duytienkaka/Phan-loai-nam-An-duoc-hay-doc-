# -*- coding: utf-8 -*-
# Socket web app: upload CSV -> dự đoán -> thống kê + bảng ID
# HTML tách trong /templates. Hỗ trợ toast lỗi, biểu đồ, tải CSV riêng.
import socket, threading, traceback, base64, io, sys, json
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

# ===================== CẤU HÌNH =====================
HOST = "127.0.0.1"
PORT = 8000
MODEL_PATH = "Phan-loai-nam\\mushroom_pipeline.joblib"
TEMPLATES_DIR = Path("Phan-loai-nam\\templates")
INDEX_TMPL = TEMPLATES_DIR / "index.html"
RESULT_TMPL = TEMPLATES_DIR / "result.html"
# ====================================================

# ---------- Load model ----------
try:
    PIPELINE = joblib.load(MODEL_PATH)
except Exception as e:
    print("[!] Không thể load model:", e, file=sys.stderr)
    PIPELINE = None

# ---------- Template helpers ----------
def load_template(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"<h1>500</h1><p>Không đọc được template {path}: {e}</p>"

def render_template(template_str: str, **kwargs) -> str:
    html = template_str
    for k, v in kwargs.items():
        html = html.replace(f"[[{k}]]", str(v))
    return html

# ---------- HTTP helpers ----------
def http_response(status_code=200, reason="OK", headers=None, body=""):
    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    if headers is None:
        headers = {}
    headers.setdefault("Content-Type", "text/html; charset=utf-8")
    headers.setdefault("Content-Length", str(len(body_bytes)))
    headers.setdefault("Connection", "close")
    head = f"HTTP/1.1 {status_code} {reason}\r\n"
    for k, v in headers.items():
        head += f"{k}: {v}\r\n"
    head += "\r\n"
    return head.encode("utf-8") + body_bytes

def parse_headers(header_bytes):
    lines = header_bytes.decode("iso-8859-1").split("\r\n")
    request_line = lines[0]
    headers = {}
    for line in lines[1:]:
        if not line: continue
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return request_line, headers

# ---------- ML helpers ----------
def detect_id_column(columns):
    lowered = [c.lower() for c in columns]
    if "id" in lowered:
        return columns[lowered.index("id")]
    for c in columns:
        lc = c.lower()
        if lc.endswith("_id") or lc in ["sample_id", "mushroom_id", "index"]:
            return c
    return None

def choose_feature_columns(model, df):
    feats = getattr(model, "feature_names_in_", None)
    if feats is not None:
        return list(feats)
    id_col = detect_id_column(df.columns)
    return [c for c in df.columns if c != "class" and c != id_col]

def to_vietnamese_labels(y_pred):
    arr = np.array(y_pred)
    unique_vals = pd.unique(arr)
    mapper = {v: str(v) for v in unique_vals}
    if set(unique_vals) <= set(["p", "e"]):
        mapper.update({"p": "Độc", "e": "Không độc"})
    elif set(unique_vals) <= set([0, 1]):
        mapper.update({1: "Độc", 0: "Không độc"})
    return pd.Series([mapper.get(v, str(v)) for v in arr], name="class_vn")

def is_poisonous_label(v):
    return (isinstance(v, str) and v.lower().startswith("p")) or v == 1

def table_html(df):
    if df is None or df.empty:
        return "<p class='muted'>(trống)</p>"
    html = ["<table><thead><tr>"]
    for c in df.columns: html.append(f"<th>{c}</th>")
    html.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        html.append("<tr>")
        for c in df.columns: html.append(f"<td>{row[c]}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return "".join(html)

def ids_table_html(ids_poison, ids_edible):
    rows = []
    for x in ids_poison: rows.append(f"<tr><td>{x}</td><td class='err'>Độc</td></tr>")
    for x in ids_edible: rows.append(f"<tr><td>{x}</td><td class='ok'>Không độc</td></tr>")
    if not rows: return "<p class='muted'>(Không có ID)</p>"
    return ("<table><thead><tr><th>ID</th><th>Loại</th></tr></thead>"
            "<tbody>" + "".join(rows) + "</tbody></table>")

def parse_multipart(body, boundary_str):
    """Trả về dict: { field_name: (filename, content_bytes) }"""
    result = {}
    boundary = b"--" + boundary_str.encode("iso-8859-1")
    parts = body.split(boundary)
    for part in parts:
        if not part or part in (b'--\r\n', b'--'): continue
        if part.startswith(b"\r\n"): part = part[2:]
        if part.endswith(b"\r\n"): part = part[:-2]
        if b"\r\n\r\n" not in part: continue
        header_block, content = part.split(b"\r\n\r\n", 1)
        headers = header_block.decode("iso-8859-1").split("\r\n")
        disposition = ""
        for h in headers:
            if h.lower().startswith("content-disposition:"): disposition = h
        name = filename = None
        for seg in disposition.split(";"):
            seg = seg.strip()
            if seg.startswith("name="): name = seg.split("=",1)[1].strip().strip('"')
            elif seg.startswith("filename="): filename = seg.split("=",1)[1].strip().strip('"')
        if name: result[name] = (filename, content)
    return result

# ---------- Toast helper (render index with toast) ----------
def respond_index_with_toast(message: str, toast_type: str = "error"):
    index_tmpl = load_template(INDEX_TMPL)
    html = render_template(index_tmpl,
                           MODEL_PATH=MODEL_PATH,
                           TOAST_MESSAGE=message,
                           TOAST_TYPE=toast_type)
    return http_response(200, "OK", body=html)

# ---------- Request handler ----------
def handle_client(conn, addr):
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk: break
            data += chunk
        if not data:
            conn.sendall(http_response(400, "Bad Request", body=""))
            return

        header_bytes, rest = data.split(b"\r\n\r\n", 1)
        request_line, headers = parse_headers(header_bytes)
        method, path, *_ = request_line.split(" ")

        content_length = int(headers.get("content-length", "0"))
        body = rest
        to_read = content_length - len(rest)
        while to_read > 0:
            chunk = conn.recv(min(65536, to_read))
            if not chunk: break
            body += chunk; to_read -= len(chunk)

        if method == "GET" and path.startswith("/"):
            if path == "/" or path.startswith("/?"):
                index_tmpl = load_template(INDEX_TMPL)
                html = render_template(index_tmpl, MODEL_PATH=MODEL_PATH,
                                       TOAST_MESSAGE="", TOAST_TYPE="")
                conn.sendall(http_response(200, "OK", body=html)); return
            conn.sendall(http_response(404, "Not Found", body="Not Found")); return

        if method == "POST" and path == "/predict":
            if PIPELINE is None:
                conn.sendall(respond_index_with_toast("Không thể tải model. Kiểm tra MODEL_PATH trong server.py."))
                return

            ctype = headers.get("content-type", "")
            if "multipart/form-data" not in ctype or "boundary=" not in ctype:
                conn.sendall(respond_index_with_toast("Thiếu multipart/form-data trong yêu cầu."))
                return
            boundary = ctype.split("boundary=", 1)[1]
            form = parse_multipart(body, boundary)
            if "file" not in form:
                conn.sendall(respond_index_with_toast("Không tìm thấy trường tệp CSV."))
                return

            _, file_bytes = form["file"]
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                df.columns = [str(c).strip() for c in df.columns]
            except Exception as e:
                conn.sendall(respond_index_with_toast(f"Không đọc được CSV: {e}"))
                return

            id_col = detect_id_column(df.columns)
            feature_cols = choose_feature_columns(PIPELINE, df)
            feature_missing = [c for c in feature_cols if c not in df.columns]
            if feature_missing:
                msg = "Thiếu các cột đặc trưng mà model mong đợi: " + ", ".join(feature_missing[:25])
                if len(feature_missing) > 25: msg += f" ... (+{len(feature_missing)-25} cột nữa)"
                conn.sendall(respond_index_with_toast(msg))
                return

            X = df[feature_cols].copy()
            try:
                y_pred = PIPELINE.predict(X)
            except Exception as e:
                conn.sendall(respond_index_with_toast(f"Lỗi khi dự đoán: {e}"))
                return

            result = df.copy()
            result["pred"] = y_pred
            result["class_vn"] = to_vietnamese_labels(y_pred).values

            counts = pd.Series(y_pred, name="pred").value_counts(dropna=False).rename_axis("label").reset_index(name="count")
            counts_vn = result["class_vn"].value_counts(dropna=False).rename_axis("label_vn").reset_index(name="count")

            if id_col and id_col in result.columns:
                ids_poison = result.loc[result["pred"].apply(is_poisonous_label), id_col].tolist()
                ids_edible = result.loc[~result["pred"].apply(is_poisonous_label), id_col].tolist()
            else:
                ids_poison, ids_edible = [], []

            # CSV đầy đủ kết quả (data URI)
            csv_buf = io.StringIO(); result.to_csv(csv_buf, index=False)
            csv_b64 = base64.b64encode(csv_buf.getvalue().encode("utf-8")).decode("ascii")

            # Dữ liệu JSON cho biểu đồ & bảng tương tác
            counts_map = counts.set_index("label")["count"].to_dict()
            html = render_template(
                load_template(RESULT_TMPL),
                counts_html=table_html(counts),
                counts_vn_html=table_html(counts_vn),
                id_col=(id_col or "(không tìm thấy)"),
                ids_table_html=ids_table_html(ids_poison, ids_edible),
                csv_b64=csv_b64,
                counts_json=json.dumps(counts_map, ensure_ascii=False),
                ids_poison_json=json.dumps(ids_poison, ensure_ascii=False),
                ids_edible_json=json.dumps(ids_edible, ensure_ascii=False),
            )
            conn.sendall(http_response(200, "OK", body=html)); return

        conn.sendall(http_response(404, "Not Found", body="Not Found"))
    except Exception:
        traceback.print_exc()
        conn.sendall(http_response(500, "Internal Server Error", body="Internal Error"))
    finally:
        try: conn.close()
        except Exception: pass

def serve_forever():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT)); s.listen(5)
        print(f"[*] Listening on http://{HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    serve_forever()
