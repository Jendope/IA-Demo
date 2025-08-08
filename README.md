# Full-Stack Product Image Capture & Batch Management System

This project is a full-stack web application designed for capturing product images, managing batch-based naming conventions, and exporting data to Excel. It features a user-friendly interface that is accessible on both desktop and mobile devices, making it a versatile tool for inventory management and product cataloging.

## Features

- **📸 Image Capture**: Capture product images using your device's camera or upload from your device.
- **🤖 AI-Powered Product Name Extraction**: Automatically extract product names from images using AI.
- **║█║ Barcode Scanning**: Scan barcodes from images to automatically populate the barcode field.
- **🏷️ Batch Management**: Automatically organizes images into batches with sequential naming.
- **📝 Data Entry**: Easily add product names, prices, and quantities for each captured image.
- **📊 Data Export**: Export all product data to an Excel file with a single click.
- **📱 Responsive Design**: Fully functional on both desktop and mobile devices.
- **🔄 Dark Mode**: Switch between light and dark themes for comfortable viewing.

## Tech Stack

- **Front-End**: HTML, CSS, JavaScript
- **Back-End**: Python, Flask
- **Database**: SQLite
- **AI**: DashScope

## Setup and Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```

2.  **Create a Python Virtual Environment**:
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**:
    -   **Windows**: `.\venv\Scripts\activate`
    -   **macOS/Linux**: `source venv/bin/activate`

4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set up Environment Variables**:
    Create a `.env` file in the root directory and add your DashScope API key:
    ```
    DASHSCOPE_API_KEY=your_api_key
    ```

6.  **Initialize the Database**:
    ```bash
    python init_db.py
    ```

7.  **Run the Application**:
    ```bash
    python app.py
    ```
    The application will be accessible at `http://127.0.0.1:5000`.

## Usage

1.  **Start the Flask Server** as shown above.
2.  **Capture or Upload an Image**: Use the camera to take a photo of the product or upload an image file.
3.  **Extract Product Name**: Click the "Analyze Image" button to have the AI extract the product name.
4.  **Scan Barcode**: Capture or upload an image of the barcode and click "Detect Barcode". If no barcode is found, the field will be set to "N/A".
5.  **Enter Product Details**: Fill in the price and quantity.
6.  **Save Product**: Click "Add Product" to save the product to the database. The form will clear for the next entry.
7.  **Manage Batches**: The application automatically manages batch numbers. You can manually override the batch prefix and index if needed.
8.  **Export Data**: Click the "Export to Excel" button to download all product data.

## Project Structure

```
├── .gitignore
├── README.md
├── app.py
├── batch_config.json
├── config.py
├── init_db.py
├── migrations/
├── requirements.txt
├── static/
│   ├── app.js
│   └── style.css
├── templates/
│   └── index.html
└── uploads/
```

## Contributing

(Guidelines for contributions will be added here.)

## License

(License information will be added here.)