document.addEventListener('DOMContentLoaded', function () {
    // Theme switcher logic
    const themeSwitcher = document.getElementById('theme-switcher');
let isEditing = false;
let currentProductId = null;
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

    const startCameraBtn = document.getElementById('startCameraBtn');
    const cameraSection = document.getElementById('camera-section');
    const captureOptions = document.getElementById('capture-options');
    const backToOptions = document.getElementById('backToOptions');

    startCameraBtn.addEventListener('click', () => {
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(function (stream) {
                video.srcObject = stream;
                video.play();
                cameraSection.style.display = 'block';
                captureOptions.style.display = 'none';
            })
            .catch(function (err) {
                console.log("An error occurred: " + err);
                alert('Could not access the camera. Please check permissions.');
            });
    });

    backToOptions.addEventListener('click', () => {
        const stream = video.srcObject;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        video.srcObject = null;
        cameraSection.style.display = 'none';
        captureOptions.style.display = 'block';
    });

    snap.addEventListener('click', function () {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/png');
        capturedImages.push(dataUrl);
        updateImagePreviews();
        video.play();
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
            previewWrapper.className = 'image-preview position-relative';

            const img = document.createElement('img');
            img.src = imageData;
            previewWrapper.appendChild(img);

            const removeBtn = document.createElement('button');
            removeBtn.className = 'btn btn-sm btn-danger remove-img';
            removeBtn.innerHTML = '&times;';
            removeBtn.style.position = 'absolute';
            removeBtn.style.top = '50%';
            removeBtn.style.left = '50%';
            removeBtn.style.transform = 'translate(-50%, -50%)';
            removeBtn.onclick = () => {
                capturedImages.splice(index, 1);
                updateImagePreviews();
            };
            previewWrapper.appendChild(removeBtn);

            imagePreviews.appendChild(previewWrapper);
        });
        updateActionButtons();
    }

    function updateActionButtons() {
    const hasImages = capturedImages.length > 0;
    document.getElementById('analyzeBtn').disabled = !hasImages;
}

    // Analyze button logic
document.getElementById('analyzeBtn').addEventListener('click', () => {
    if (capturedImages.length === 0) return;
    const lastImage = capturedImages[capturedImages.length - 1];
    const analyzeBtn = document.getElementById('analyzeBtn');
    const originalHtml = analyzeBtn.innerHTML;
    analyzeBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing...`;
    analyzeBtn.disabled = true;

    fetch('/analyze_ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_data: lastImage })
    })
    .then(response => response.json())
    .then(data => {
        if (data.name) document.getElementById('productName').value = data.name;
    if (data.brand) document.getElementById('productBrand').value = data.brand;
    if (data.object_count) document.getElementById('quantity').value = data.object_count;
    // Proceed to barcode detection
    return fetch('/detect_barcode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: lastImage })
        });
    })
    .then(response => response.json())
    .then(data => {
        if (data.barcode) document.getElementById('barcode').value = data.barcode;
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred during analysis.');
    })
    .finally(() => {
        analyzeBtn.innerHTML = originalHtml;
        analyzeBtn.disabled = false;
    });
});

    // Product form submission
    document.getElementById('productForm').addEventListener('submit', function (e) {
        e.preventDefault();
        const productData = {
            name: document.getElementById('productName').value,
            brand: document.getElementById('productBrand').value,
            barcode: document.getElementById('barcode').value,
            price: document.getElementById('price').value,
            quantity: document.getElementById('quantity').value,
            images: capturedImages
        };

        const url = isEditing ? `/update_product/${currentProductId}` : '/add_product';
fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(productData)
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        loadProducts();
        loadBatch();
        document.getElementById('productName').value = '';
        document.getElementById('productBrand').value = '';
        document.getElementById('barcode').value = '';
        document.getElementById('price').value = '';
        document.getElementById('quantity').value = '';
        capturedImages = [];
        updateImagePreviews();
        updateActionButtons();
        isEditing = false;
        currentProductId = null;
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
                        <td>${product.brand}</td>
                        <td>${product.barcode}</td>
                        <td>${product.price}</td>
                        <td>${product.quantity}</td>
                        <td>${new Date(product.timestamp).toLocaleString()}</td>
                        <td>
                        <td>
    <button class="btn btn-sm btn-primary me-1" onclick="editProduct('${product.id}')"><i class="bi bi-pencil"></i></button>
    <button class="btn btn-sm btn-danger" onclick="deleteProduct('${product.id}')"><i class="bi bi-trash"></i></button>
</td>                        </td>
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

window.editProduct = async function(id) {
    isEditing = true;
    currentProductId = id;
    try {
        const response = await fetch(`/get_product/${id}`);
        const product = await response.json();
        if (product.error) {
            alert(product.error);
            return;
        }
        document.getElementById('productName').value = product.name;
        document.getElementById('productBrand').value = product.brand || '';
        document.getElementById('barcode').value = product.barcode;
        document.getElementById('price').value = product.price;
        document.getElementById('quantity').value = product.quantity;

        capturedImages = [];
        const imagePromises = product.images.map(async (path) => {
            const res = await fetch(`/${path}`);
            const blob = await res.blob();
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
        });
        capturedImages = await Promise.all(imagePromises);
        updateImagePreviews();
    } catch (error) {
        console.error('Error loading product for edit:', error);
        alert('Failed to load product for editing.');
    }
};



    // Data management
    document.getElementById('exportCsv').addEventListener('click', () => {
        window.location.href = '/export_csv';
    });

    document.getElementById('resetDataBtn').addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all data? This cannot be undone.')) {
            fetch('/reset_data', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loadProducts();
                        loadBatch();
                        alert('Data reset successfully.');
                    } else {
                        alert('Error resetting data: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Reset error:', error);
                    alert('An error occurred during reset.');
                });
        }
    });

    // Initial load
    loadBatch();
    loadProducts();
});