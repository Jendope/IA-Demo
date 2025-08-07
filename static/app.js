document.addEventListener('DOMContentLoaded', function () {
    // Theme switcher logic
    const themeSwitcher = document.getElementById('theme-switcher');
    const htmlElement = document.documentElement;

    themeSwitcher.addEventListener('change', () => {
        if (themeSwitcher.checked) {
            htmlElement.setAttribute('data-bs-theme', 'dark');
        } else {
            htmlElement.setAttribute('data-bs-theme', 'light');
        }
    });

    // Camera and image capture logic
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const snap = document.getElementById('snap');
    const imagePreviews = document.getElementById('image-previews');
    const imageUpload = document.getElementById('imageUpload');
    let capturedImages = [];

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
        .then(function (stream) {
            video.srcObject = stream;
            video.play();
        })
        .catch(function (err) {
            console.log("An error occurred: " + err);
        });

    snap.addEventListener('click', function () {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/png');
        capturedImages.push(dataUrl);
        updateImagePreviews();
    });

    imageUpload.addEventListener('change', function(e) {
        const files = e.target.files;
        for (const file of files) {
            const reader = new FileReader();
            reader.onload = function(event) {
                capturedImages.push(event.target.result);
                updateImagePreviews();
            }
            reader.readAsDataURL(file);
        }
    });

    function updateImagePreviews() {
        imagePreviews.innerHTML = '';
        capturedImages.forEach((imageData, index) => {
            const previewWrapper = document.createElement('div');
            previewWrapper.className = 'image-preview';

            const img = document.createElement('img');
            img.src = imageData;

            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-img';
            removeBtn.innerHTML = '&times;';
            removeBtn.onclick = () => {
                capturedImages.splice(index, 1);
                updateImagePreviews();
            };

            previewWrapper.appendChild(img);
            previewWrapper.appendChild(removeBtn);
            imagePreviews.appendChild(previewWrapper);
        });
        updateActionButtons();
    }

    function updateActionButtons() {
        const hasImages = capturedImages.length > 0;
        document.getElementById('detectBarcodeBtn').disabled = !hasImages;
        document.getElementById('extractTextBtn').disabled = !hasImages;
        document.getElementById('analyzeImage').disabled = !hasImages;
    }



    // OCR and Barcode logic
    document.getElementById('extractTextBtn').addEventListener('click', () => {
        if (capturedImages.length === 0) return;
        const lastImage = capturedImages[capturedImages.length - 1];
        fetch('/extract_product_name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: lastImage })
        })
        .then(response => response.json())
        .then(data => {
            if (data.product_name) {
                document.getElementById('productName').value = data.product_name;
            } else {
                alert('Could not extract product name.');
            }
        });
    });

    document.getElementById('analyzeImage').addEventListener('click', () => {
        if (capturedImages.length === 0) return;
        const lastImage = capturedImages[capturedImages.length - 1];

        const analyzeBtn = document.getElementById('analyzeImage');
        const originalHtml = analyzeBtn.innerHTML;
        analyzeBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing...`;
        analyzeBtn.disabled = true;

        fetch('/analyze_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: lastImage })
        })
        .then(response => response.json())
        .then(data => {
            if (data.description) {
                document.getElementById('productName').value = data.description;
            } else {
                alert('AI analysis failed.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during AI analysis.');
        })
        .finally(() => {
            analyzeBtn.innerHTML = originalHtml;
            analyzeBtn.disabled = capturedImages.length === 0;
        });
    });

    document.getElementById('detectBarcodeBtn').addEventListener('click', () => {
        if (capturedImages.length === 0) return;
        const lastImage = capturedImages[capturedImages.length - 1];
        const productName = document.getElementById('productName').value;
        fetch('/detect_barcode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: lastImage, product_name: productName })
        })
        .then(response => response.json())
        .then(data => {
            if (data.barcode) {
                document.getElementById('barcode').value = data.barcode;
            } else {
                alert('No barcode detected.');
            }
        });
    });


    // Product form submission
    document.getElementById('productForm').addEventListener('submit', function (e) {
        e.preventDefault();
        const productData = {
            name: document.getElementById('productName').value,
            barcode: document.getElementById('barcode').value,
            price: document.getElementById('price').value,
            quantity: document.getElementById('quantity').value,
            images: capturedImages
        };

        fetch('/add_product', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(productData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadProducts();
                this.reset();
                capturedImages = [];
                updateImagePreviews();
                updateActionButtons();
            }
        });
    });

    // Batch management
    const batchPrefix = document.getElementById('batchPrefix');
    const batchIndex = document.getElementById('batchIndex');
    const batchStatus = document.getElementById('batchStatus');

    function loadBatch() {
        fetch('/get_batch')
            .then(response => response.json())
            .then(data => {
                batchPrefix.value = data.prefix;
                batchIndex.value = data.index;
                batchStatus.textContent = `Batch: ${data.prefix}${data.index}`;
            });
    }

    document.getElementById('updateBatch').addEventListener('click', () => {
        fetch('/set_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prefix: batchPrefix.value, index: batchIndex.value })
        })
        .then(() => loadBatch());
    });

    // Product list
    const productList = document.getElementById('productList');

    function loadProducts() {
        fetch('/get_products')
            .then(response => response.json())
            .then(data => {
                productList.innerHTML = '';
                data.forEach(product => {
                    const row = document.createElement('tr');
                    let thumbnailUrl = 'data:image/svg+xml;charset=UTF-8,%3csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'80\' height=\'80\' viewBox=\'0 0 80 80\'%3e%3crect width=\'80\' height=\'80\' fill=\'%23ccc\'/%3e%3c/svg%3e';
                    if (product.images.length > 0) {
                        const imagePath = product.images[0].replace(/\\/g, '/');
                        const pathParts = imagePath.split('/');
                        const relativePath = pathParts.slice(-2).join('/');
                        thumbnailUrl = `/${relativePath}`;
                    }
                    row.innerHTML = `
                        <td>${product.id}</td>
                        <td><img src="${thumbnailUrl}" class="product-thumbnail"></td>
                        <td>${product.name}</td>
                        <td>${product.barcode}</td>
                        <td>${product.price}</td>
                        <td>${product.quantity}</td>
                        <td>${new Date(product.timestamp).toLocaleString()}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="deleteProduct('${product.id}')"><i class="bi bi-trash"></i></button>
                        </td>
                    `;
                    productList.appendChild(row);
                });
            });
    }

    window.deleteProduct = function(id) {
        if (confirm('Are you sure you want to delete this product?')) {
            fetch(`/delete_product/${id}`, { method: 'DELETE' })
                .then(() => loadProducts());
        }
    }

    // AI Image Analysis
    const analyzeImageBtn = document.getElementById('analyzeImage');
    const aiAnalysisResult = document.getElementById('aiAnalysis');

    analyzeImageBtn.addEventListener('click', () => {
        if (capturedImages.length === 0) {
            alert('Please capture an image first.');
            return;
        }
        const lastImage = capturedImages[capturedImages.length - 1];
        aiAnalysisResult.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';

        fetch('/analyze_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: lastImage })
        })
        .then(response => response.json())
        .then(data => {
            if (data.description) {
                aiAnalysisResult.innerHTML = `<p>${data.description}</p>`;
                // Also, populate the product name field
                document.getElementById('productName').value = data.description;
            } else {
                aiAnalysisResult.innerHTML = '<p class="text-danger">Failed to analyze image.</p>';
            }
        })
        .catch(error => {
            console.error('Error during AI analysis:', error);
            aiAnalysisResult.innerHTML = '<p class="text-danger">An error occurred during analysis.</p>';
        });
    });

    document.getElementById('analyzeImage').addEventListener('click', () => {
        if (capturedImages.length === 0) {
            alert('Please capture or upload an image first.');
            return;
        }

        const lastImage = capturedImages[capturedImages.length - 1];
        analysisResult.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p class="mt-2">Analyzing image...</p></div>';
        aiAnalysisModal.show();

        fetch('/analyze_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: lastImage })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                analysisResult.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            } else {
                analysisResult.innerHTML = `<div class="alert alert-success">${data.description}</div>`;
            }
        })
        .catch(error => {
            analysisResult.innerHTML = `<div class="alert alert-danger">Error analyzing image: ${error.message}</div>`;
        });
    });

    // Data management
    document.getElementById('exportExcel').addEventListener('click', () => {
        window.location.href = '/export_excel';
    });

    document.getElementById('resetDataBtn').addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all data? This cannot be undone.')) {
            fetch('/reset_data', { method: 'POST' })
                .then(() => {
                    loadProducts();
                    loadBatch();
                });
        }
    });

    // Initial load
    loadBatch();
    loadProducts();
});