import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
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

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Product(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
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
def index():
    return render_template('index.html')

@app.route('/detect_barcode', methods=['POST'])
def detect_barcode_route():
    data = request.get_json()
    if 'image_data' not in data:
        return jsonify({'error': 'No image data'}), 400
    try:
        image = read_image_from_data_url(data['image_data'])
        barcodes = decode(image)
        if barcodes:
            return jsonify({'barcode': barcodes[0].data.decode('utf-8')})
        return jsonify({'barcode': ''})
    except Exception as e:
        app.logger.error(f"Error during barcode detection: {e}")
        return jsonify({'error': 'Failed to process image for barcode detection'}), 500

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        batch_config = get_batch_config()
        product_id = f"{batch_config['prefix']}{batch_config['index']}"

        image_paths = []
        if 'images' in data and data['images']:
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            for i, image_data_url in enumerate(data['images']):
                try:
                    header, encoded = image_data_url.split(',', 1)
                    image_data = base64.b64decode(encoded)
                    image = Image.open(BytesIO(image_data))
                    filename = f"{product_id}_{i}.png"
                    filepath = os.path.join(upload_folder, filename)
                    image.save(filepath)
                    # Store the relative path for URL generation
                    relative_path = os.path.join('uploads', filename).replace('\\', '/')
                    image_paths.append(relative_path)
                except Exception as e:
                    app.logger.error(f"Could not process image {i} for product {product_id}: {e}")

        new_product = Product(
            id=product_id,
            name=data['name'],
            barcode=data['barcode'],
            price=float(data['price']),
            quantity=int(data['quantity']),
            images=image_paths, # Store file paths instead of base64 data
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

@app.route('/get_products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/delete_product/<string:product_id>', methods=['DELETE'])
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
        json.dump(config, f, indent=4)

@app.route('/get_batch', methods=['GET'])
def get_batch():
    return jsonify(get_batch_config())

@app.route('/set_batch', methods=['POST'])
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

@app.route('/export_excel', methods=['GET'])
def export_excel():
    products = Product.query.all()
    if not products:
        return "No data to export", 404

    data_for_df = []
    for p in products:
        data_for_df.append({
            'ID': p.id,
            'Name': p.name,
            'Barcode': p.barcode,
            'Price': p.price,
            'Quantity': p.quantity,
            'Timestamp': p.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })

    df = pd.DataFrame(data_for_df)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')
    output.seek(0)
    
    return send_file(
        output, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        as_attachment=True, 
        download_name='products.xlsx'
    )

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)

@app.route('/reset_data', methods=['POST'])
def reset_data():
    try:
        db.session.query(Product).delete()
        save_batch_config({'prefix': 'A', 'index': 1})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error resetting data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)