import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, Response, redirect, url_for, flash
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()  # Load environment variables from .env file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pyzbar.pyzbar import decode
import pandas as pd
import json
import base64
from io import BytesIO
from PIL import Image
from config import Config
from datetime import datetime
import dashscope
from dashscope.api_entities.dashscope_response import Role
from http import HTTPStatus
import re
from openai import OpenAI

app = Flask(__name__)
app.config.from_object(Config)

# Configure the DashScope client
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
if not dashscope.api_key:
    print("Warning: DASHSCOPE_API_KEY is not set. Please update your .env file.")

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Product(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    barcode = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    images_json = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @property
    def images(self):
        return json.loads(self.images_json)

    @images.setter
    def images(self, value):
        self.images_json = json.dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'barcode': self.barcode,
            'price': self.price,
            'quantity': self.quantity,
            'images': self.images,
            'timestamp': self.timestamp.isoformat()
        }

BATCH_CONFIG_FILE = 'batch_config.json'

def read_image_from_data_url(data_url):
    header, encoded = data_url.split(',', 1)
    image_data = base64.b64decode(encoded)
    image = Image.open(BytesIO(image_data))
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



@app.route('/extract_product_name', methods=['POST'])
@login_required
def extract_product_name():
    data = request.get_json()
    if 'image_data' not in data:
        return jsonify({'error': 'No image data'}), 400

    try:
        header, encoded = data['image_data'].split(',', 1)
        image_data = base64.b64decode(encoded)
        
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        temp_image_path = os.path.join(upload_folder, 'temp_product_name_image.png')
        with open(temp_image_path, 'wb') as f:
            f.write(image_data)

        abs_temp_image_path = os.path.abspath(temp_image_path)
        local_file_url = f'file://{abs_temp_image_path}'

        messages = [
            {
                'role': Role.USER,
                'content': [
                    {'image': image_data_url},
                    {'text': 'Extract the full product name from the image, including the brand and any specific variations. For example, if the product is "St. Ives Soothing Body Lotion Oatmeal & Shea Butter," return that exact text. Do not add any extra words or labels.'}
                ]
            }
        ]
        response = dashscope.MultiModalConversation.call(
            model='qwen-vl-max',
            messages=messages
        )

        if response.status_code == HTTPStatus.OK:
            product_name = response.output.choices[0].message.content[0]['text']
            return jsonify({'product_name': product_name})
        else:
            app.logger.error(f"Error from DashScope API: {response.code} - {response.message}")
            return jsonify({'error': 'Failed to extract product name'}), 500

    except Exception as e:
        app.logger.error(f"Error during product name extraction: {e}")
        return jsonify({'error': 'Failed to extract product name'}), 500
    

@app.route('/detect_barcode', methods=['POST'])
@login_required
def detect_barcode_route():
    data = request.get_json()
    if 'image_data' not in data:
        return jsonify({'error': 'No image data'}), 400
    try:
        image = read_image_from_data_url(data['image_data'])
        barcodes = decode(image)
        if barcodes:
            return jsonify({'barcode': barcodes[0].data.decode('utf-8')})
        return jsonify({'barcode': 'N/A'})
    except Exception as e:
        app.logger.error(f"Error during barcode detection: {e}")
        return jsonify({'error': 'Failed to process image for barcode detection'}), 500

def save_images(product_id, images_data):
    image_paths = []
    if images_data:
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        for i, image_data_url in enumerate(images_data):
            try:
                header, encoded = image_data_url.split(',', 1)
                image_data = base64.b64decode(encoded)
                image = Image.open(BytesIO(image_data))
                filename = f"{product_id}_{i}.png"
                filepath = os.path.join(upload_folder, filename)
                image.save(filepath)
                relative_path = os.path.join('uploads', filename).replace('\\', '/')
                image_paths.append(relative_path)
            except Exception as e:
                app.logger.error(f"Could not process image {i} for product {product_id}: {e}")
    return image_paths

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    data = request.get_json()
    try:
        batch_config = get_batch_config()
        product_id = f"{batch_config['prefix']}{batch_config['index']}"

        image_paths = save_images(product_id, data.get('images', []))

        new_product = Product(
            id=product_id,
            name=data['name'],
            brand=data.get('brand'),
            barcode=data['barcode'],
            price=float(data['price']),
            quantity=int(data['quantity']),
            images=image_paths,
            timestamp=datetime.now()
        )
        db.session.add(new_product)

        batch_config['index'] += 1
        save_batch_config(batch_config)

        db.session.commit()
        return jsonify({'success': True, 'product_id': product_id})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_product/<product_id>', methods=['POST'])
@login_required
def update_product(product_id):
    data = request.get_json()
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404

        product.name = data['name']
        product.brand = data.get('brand', product.brand)
        product.barcode = data['barcode']
        product.price = float(data['price'])
        product.quantity = int(data['quantity'])

        # Delete old images
        for old_path in product.images:
            full_old_path = os.path.join(app.root_path, old_path)
            if os.path.exists(full_old_path):
                os.remove(full_old_path)

        image_paths = save_images(product_id, data.get('images', []))
        product.images = image_paths

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_products', methods=['GET'])
@login_required
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/get_product/<product_id>', methods=['GET'])
@login_required
def get_product(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify(product.to_dict())
    return jsonify({'error': 'Product not found'}), 404

@app.route('/products.json')
@login_required
def get_products_json():
    products = Product.query.all()
    products_dict = [p.to_dict() for p in products]
    json_string = json.dumps(products_dict, indent=4)
    return Response(json_string, mimetype='application/json')

@app.route('/delete_product/<string:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    try:
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'}), 404
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_batch_config():
    try:
        with open(BATCH_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'prefix': 'A', 'index': 1}

def save_batch_config(config):
    with open(BATCH_CONFIG_FILE, 'w') as f:
        json.dump(config, f)

@app.route('/get_batch', methods=['GET'])
@login_required
def get_batch():
    return jsonify(get_batch_config())

@app.route('/set_batch', methods=['POST'])
@login_required
def set_batch():
    data = request.get_json()
    try:
        config = {
            'prefix': data.get('prefix', 'A'),
            'index': int(data.get('index', 1))
        }
        save_batch_config(config)
        return jsonify({'success': True})
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': 'Invalid data format'}), 400

@app.route('/analyze_full', methods=['POST'])
@login_required
def analyze_full():
    data = request.get_json()
    if 'image_data' not in data:
        return jsonify({'error': 'No image data'}), 400

    try:
        image = read_image_from_data_url(data['image_data'])

        # First, try to detect barcode using pyzbar
        barcodes = decode(image)
        barcode = barcodes[0].data.decode('utf-8') if barcodes else None

        # Save image for AI analysis
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        temp_image_path = os.path.join(upload_folder, 'temp_analysis_image.png')
        cv2.imwrite(temp_image_path, image)

        abs_temp_image_path = os.path.abspath(temp_image_path)
        local_file_url = f'file://{abs_temp_image_path}'

        # AI prompt for name and brand
        messages = [
            {
                'role': Role.USER,
                'content': [
                    {'image': local_file_url},
                    {'text': 'Respond ONLY with a valid JSON object in this format: {"name": "full product name without brand", "brand": "brand name", "barcode": "number or null if not found"}. Do not include any explanations, code blocks, or additional text. Ensure the response is pure JSON.'}
                ]
            }
        ]
        response = dashscope.MultiModalConversation.call(
            model='qwen-vl-max',
            messages=messages
        )

        if response.status_code == HTTPStatus.OK:
            ai_result = response.output.choices[0].message.content[0]['text']
            app.logger.info(f"AI raw response: {ai_result}")
            try:
                # Extract JSON from response
                match = re.search(r'\{.*\}', ai_result, re.DOTALL)
                if match:
                    ai_result_clean = match.group(0)
                else:
                    ai_result_clean = ai_result
                details = json.loads(ai_result_clean)
                name = details.get('name', '')
                brand = details.get('brand', '')
                ai_barcode = details.get('barcode')
                # Use AI barcode if pyzbar failed
                if not barcode and ai_barcode and ai_barcode != 'null':
                    barcode = ai_barcode
            except json.JSONDecodeError as e:
                app.logger.error(f"JSON decode error: {str(e)}")
                return jsonify({'error': 'Invalid AI response format'}), 500

            return jsonify({'name': name, 'brand': brand, 'barcode': barcode or 'N/A'})
        

    except Exception as e:
        app.logger.error(f"Error during full analysis: {e}")
        return jsonify({'error': 'Failed to analyze'}), 500


@app.route('/analyze_ai', methods=['POST'])
@login_required
def analyze_ai():
    data = request.get_json()
    if 'image_data' not in data:
        return jsonify({'error': 'No image data'}), 400

    try:
        image_data_url = data['image_data']

        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        completion = client.chat.completions.create(
            model="qwen-vl-max",
            messages=[
                {"role": "user",
                 "content": [
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                    {"type": "text", "text": 'You are an assistant that identifies product details and counts similar objects from an image. \n\n Step 1: Look at the product image and read any visible text and numbers. \n Step 2: Identify the PRODUCT NAME — the main title or description of the item. \n Step 3: Identify the BRAND NAME — the manufacturer or company name, often from a logo. \n Step 4: Identify the BARCODE NUMBER — the numeric code found on the barcode (if visible). \n Step 5: Count the number of similar objects/products visible in the image (e.g., if multiple identical items are shown, count them). \n Step 6: Output only in the following JSON format: \n\n { \n   "product_name": "<product name here>", \n   "brand_name": "<brand name here>", \n   "barcode_number": "<barcode number here or \'not visible\'>", \n   "object_count": <integer count of similar objects> \n } \n\n Do not include extra text or explanations.'}
                 ]}
            ],
            top_p=0.8,
            temperature=1
        )
        ai_result = completion.choices[0].message.content
        app.logger.info(f"AI raw response: {ai_result}")
        try:
            match = re.search(r'\{.*\}', ai_result, re.DOTALL)
            if match:
                ai_result_clean = match.group(0)
            else:
                ai_result_clean = ai_result
            details = json.loads(ai_result_clean)
            product_name = details.get('product_name', '')
            brand_name = details.get('brand_name', '')
            barcode_number = details.get('barcode_number', 'not visible')
            object_count = details.get('object_count', 1)  # Default to 1 if not provided
            return jsonify({'name': product_name, 'brand': brand_name, 'barcode': barcode_number, 'object_count': object_count})
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON decode error: {str(e)}")
            return jsonify({'error': 'Invalid AI response format'}), 500

    except Exception as e:
        app.logger.error(f"Error during AI analysis: {e}")
        return jsonify({'error': 'Failed to analyze'}), 500

@app.route('/export_csv', methods=['GET'])
@login_required
def export_csv():
    products = Product.query.all()
    if not products:
        return "No data to export", 404

    data_for_df = []
    for p in products:
        data_for_df.append({
            'ID': p.id,
            'Name': p.name,
            'Brand': p.brand,
            'Barcode': p.barcode,
            'Price': p.price,
            'Quantity': p.quantity,
            'Timestamp': p.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })

    df = pd.DataFrame(data_for_df)
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return send_file(
        output, 
        mimetype='text/csv', 
        as_attachment=True, 
        download_name='products.csv'
    )

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)

@app.route('/reset_data', methods=['POST'])
@login_required
def reset_data():
    try:
        app.logger.info("--- Starting data reset process ---")
        # Clear the uploads folder
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        app.logger.info(f"Upload folder is: {upload_folder}")
        if os.path.exists(upload_folder):
            app.logger.info("Upload folder exists. Clearing files...")
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path) and filename != '.gitkeep':
                    app.logger.info(f"Deleting file: {file_path}")
                    os.unlink(file_path)
            app.logger.info("Finished clearing upload folder.")
        else:
            app.logger.info("Upload folder does not exist. Skipping file clearing.")

        # Reset the database
        app.logger.info("Resetting database...")
        db.session.query(Product).delete(synchronize_session=False)
        app.logger.info("Products deleted. Resetting batch config...")
        save_batch_config({'prefix': 'A', 'index': 1})
        app.logger.info("Batch config reset. Committing changes...")
        db.session.commit()
        app.logger.info("--- Data reset process completed successfully ---")
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"--- ERROR during data reset: {e} ---")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)