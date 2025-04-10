// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const compressBtn = document.getElementById('compressBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progress = document.getElementById('progress');
    const progressText = document.getElementById('progressText');

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.style.borderColor = 'var(--primary-color)';
            dropZone.style.background = 'rgba(0, 188, 212, 0.05)';
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.style.borderColor = '';
            dropZone.style.background = '';
        });
    });

    dropZone.addEventListener('drop', handleDrop);
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0]; // Only handle first file
            showFileInfo(file);
            compressBtn.disabled = false;
        }
    }

    function showFileInfo(file) {
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        fileInfo.style.display = 'block';
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function updateProgress(percent) {
        progress.style.width = `${percent}%`;
        progressText.textContent = `Processing... ${percent}%`;
    }

    compressBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        const targetSize = document.getElementById('targetSize').value;
        if (targetSize < 1) {
            progressText.textContent = 'Error: Target size must be at least 1KB';
            return;
        }

        progressContainer.style.display = 'block';
        compressBtn.disabled = true;
        compressBtn.querySelector('.loading-spinner').style.display = 'block';
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('targetSize', targetSize);

        try {
            updateProgress(50);  // Show 50% progress while processing

            const response = await fetch('/api/compress', {
                method: 'POST',
                body: formData
            });

            updateProgress(100);

            if (response.ok) {
                const blob = await response.blob();
                // Verify the size is close to target
                const actualSize = blob.size / 1024; // Convert to KB
                const targetSizeKB = parseFloat(targetSize);
                
                if (Math.abs(actualSize - targetSizeKB) > 1) {
                    progressText.textContent = `Warning: Achieved ${Math.round(actualSize)}KB (Target: ${targetSizeKB}KB)`;
                }

                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `compressed_${file.name}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);

                // Reset UI after successful compression
                setTimeout(() => {
                    fileInput.value = '';
                    fileInfo.style.display = 'none';
                    progressContainer.style.display = 'none';
                    compressBtn.disabled = true;
                }, 2000);
            } else {
                throw new Error('Compression failed');
            }
        } catch (error) {
            progressText.textContent = 'Error: Compression failed';
            progress.style.backgroundColor = '#ff4757';
        } finally {
            compressBtn.querySelector('.loading-spinner').style.display = 'none';
            compressBtn.disabled = false;
        }
    });

});
// Add these variables at the top
let uploadAnimation = document.getElementById('uploadAnimation');
let uploadStatus = document.getElementById('uploadStatus');
let uploadProgress = document.getElementById('uploadProgress');

// Update handleFiles function
function handleFiles(files) {
    if (files.length === 0) return;
    
    const file = files[0];
    const maxSize = 100 * 1024 * 1024; // 100MB
    
    if (file.size > maxSize) {
        alert('File size exceeds 100MB limit');
        return;
    }
    
    showFileInfo(file);
    compressButton.disabled = false;
}

// Update compress button click handler
compressButton.addEventListener('click', async () => {
    try {
        const file = fileInput.files[0];
        const targetSize = parseInt(targetSizeInput.value);
        
        if (!file || targetSize < 1) return;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('targetSize', targetSize);
        
        uploadAnimation.style.display = 'block';
        uploadStatus.textContent = 'Uploading...';
        
        const response = await fetch('/api/compress', {
            method: 'POST',
            body: formData,
            onUploadProgress: (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                uploadProgress.textContent = `${percentCompleted}%`;
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        uploadStatus.textContent = 'Processing...';
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `compressed_${file.name}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        uploadStatus.textContent = 'Complete!';
        setTimeout(() => {
            uploadAnimation.style.display = 'none';
        }, 1000);
        
    } catch (error) {
        console.error('Error:', error);
        uploadStatus.textContent = 'Error: ' + error.message;
        uploadProgress.style.color = 'red';
    }
});
