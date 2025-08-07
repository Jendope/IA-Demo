# Full-Stack Product Image Capture & Batch Management System

This project is a full-stack web application designed for capturing product images, managing batch-based naming conventions, and exporting data to Excel. It features a user-friendly interface that is accessible on both desktop and mobile devices, making it a versatile tool for inventory management and product cataloging.

## Features

- **📸 Image Capture**: Capture product images using your device's camera.
- **🏷️ Batch Management**: Automatically organizes images into batches with sequential naming.
- **📝 Data Entry**: Easily add product names and codes for each captured image.
- **📊 Data Export**: Export all product data to an Excel file with a single click.
- **📱 Responsive Design**: Fully functional on both desktop and mobile devices.

## Tech Stack

- **Front-End**: HTML, CSS, JavaScript
- **Back-End**: Python, Flask
- **Database**: SQLite

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

5.  **Run the Application**:
    ```bash
    flask run
    ```
    The application will be accessible at `http://127.0.0.1:5000`.

## Usage

1.  **Start the Flask Server** as shown above.
2.  **Capture Images**: Use the camera preview to position your product and click the capture button.
3.  **Enter Product Details**: After capturing an image, input the product name and code.
4.  **Manage Batches**: The application automatically manages batch numbers. Edit `batch_config.json` for manual changes.
5.  **Export Data**: Click the "Export to Excel" button to download all product data.

## Project Structure

```
├── .gitignore
├── README.md
├── app.py
├── batch_config.json
├── config.py
├── init_db.py
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