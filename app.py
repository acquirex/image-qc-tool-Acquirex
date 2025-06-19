from flask import Flask, render_template, request, jsonify, url_for
import zipfile, os, tempfile, requests
import pandas as pd
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
import time
import shutil

app = Flask(__name__, template_folder="templates", static_folder="static")

# ✅ Replace this with your actual ImgBB API key
IMGBB_API_KEY = '544cef9bb31caf5382a123beb593e864'

# 🔁 Upload function using ImgBB API
def upload_to_imgbb(img_path):
    with open(img_path, "rb") as file:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": IMGBB_API_KEY,
        }
        files = {
            "image": file,
        }
        response = requests.post(url, data=payload, files=files)

    if response.status_code == 200:
        return response.json()['data']['url']
    return "Upload Failed"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/product-qc')
def product_qc():
    return render_template('product_qc.html')

@app.route('/a-plus-qc')
def a_plus_qc():
    return render_template('a_plus_qc.html')

@app.route('/link-generator')
def link_generator():
    return render_template('link_generator.html')

@app.route('/generate-links', methods=['POST'])
def generate_links():
    start_time = time.time()
    
    zip_file = request.files['zip_file']
    temp_dir = tempfile.mkdtemp()

    zip_path = os.path.join(temp_dir, secure_filename(zip_file.filename))
    zip_file.save(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    result_data = []
    excel_data = []

    for folder in os.listdir(temp_dir):
        folder_path = os.path.join(temp_dir, folder)
        if os.path.isdir(folder_path):
            row = [folder]
            images = []

            image_names = sorted(os.listdir(folder_path))
            image_paths = [os.path.join(folder_path, img) for img in image_names]

            with ThreadPoolExecutor(max_workers=10) as executor:
                urls = list(executor.map(upload_to_imgbb, image_paths))

            for img_name, url in zip(image_names, urls):
                row.append(url)
                images.append({'filename': img_name, 'url': url})

            result_data.append({'mpn': folder, 'images': images})
            excel_data.append(row)

    if excel_data:
        max_images = max(len(row) for row in excel_data)
    else:
        max_images = 1

    columns = ['MPN'] + [f'Image {i}' for i in range(1, max_images)]
    df = pd.DataFrame(excel_data, columns=columns)
    os.makedirs("static/exports", exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_excel = os.path.join("static/exports", f"ImageLinks_{timestamp}.xlsx")
    df.to_excel(output_excel, index=False)

    shutil.rmtree(temp_dir)

    excel_filename = os.path.basename(output_excel)
    processing_time = round(time.time() - start_time, 2)

    return jsonify({
        "excel_url": url_for('static', filename='exports/' + excel_filename),
        "processing_time": processing_time
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
