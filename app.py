# app.py
from flask import Flask, request, send_file, render_template, jsonify
import os
from werkzeug.utils import secure_filename
from PIL import Image
import PyPDF2
import io
from PyPDF2 import PdfReader, PdfWriter
import sys
import logging
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Increase maximum content length to 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'document': {'pdf'}
}

def allowed_file(filename):
    """Check if the file extension is allowed."""
    try:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in \
               {ext for exts in ALLOWED_EXTENSIONS.values() for ext in exts}
    except Exception as e:
        logging.error(f"Error checking file extension: {str(e)}")
        return False

def get_file_type(filename):
    """Determine file type from extension."""
    ext = filename.rsplit('.', 1)[1].lower()
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return None

def compress_image(image_file, target_size_kb):
    """
    Compress image to exact target size using binary search.
    Returns: (compressed_file, success, message)
    """
    try:
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Convert target size from KB to bytes
        target_bytes = int(target_size_kb * 1024)
        
        # Check if original size is already smaller
        temp_buffer = io.BytesIO()
        img.save(temp_buffer, format='JPEG', quality=100)
        if temp_buffer.tell() <= target_bytes:
            temp_buffer.seek(0)
            return temp_buffer, True, f"Original size ({temp_buffer.tell() // 1024}KB) is already smaller than target"
        
        # Binary search for the quality that gives us the exact target size
        min_quality = 1
        max_quality = 100
        best_quality = 50
        best_size = None
        best_output = None
        attempts = 0
        max_attempts = 20  # Prevent infinite loops
        
        while min_quality <= max_quality and attempts < max_attempts:
            attempts += 1
            current_quality = (min_quality + max_quality) // 2
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=current_quality, optimize=True)
            current_size = output.tell()
            
            # Update best if this is closer to target
            if best_size is None or abs(current_size - target_bytes) < abs(best_size - target_bytes):
                best_quality = current_quality
                best_size = current_size
                best_output = output
            
            if current_size > target_bytes:
                max_quality = current_quality - 1
            else:
                min_quality = current_quality + 1
            
            # Break if we're within 0.5KB of target size
            if abs(current_size - target_bytes) <= 512:  # 0.5KB in bytes
                break
        
        if best_output is None:
            return None, False, "Failed to achieve target size"
        
        best_output.seek(0)
        actual_size = best_output.tell() // 1024
        return best_output, True, f"Compressed to {actual_size}KB (Quality: {best_quality}%)"
    
    except Exception as e:
        logging.error(f"Image compression error: {str(e)}")
        return None, False, f"Image compression failed: {str(e)}"

def compress_pdf(pdf_file, target_size_kb):
    """
    Compress PDF to target size using binary search on image quality.
    Returns: (compressed_file, success, message)
    """
    try:
        target_bytes = int(target_size_kb * 1024)
        
        # Read original PDF
        pdf_reader = PdfReader(pdf_file)
        
        # Check if original size is already smaller
        temp_buffer = io.BytesIO()
        PdfWriter().write(temp_buffer)
        if temp_buffer.tell() <= target_bytes:
            temp_buffer.seek(0)
            return temp_buffer, True, f"Original size ({temp_buffer.tell() // 1024}KB) is already smaller than target"
        
        # Binary search for compression level
        min_quality = 1
        max_quality = 100
        best_quality = 50
        best_size = None
        best_output = None
        attempts = 0
        max_attempts = 20
        
        while min_quality <= max_quality and attempts < max_attempts:
            attempts += 1
            current_quality = (min_quality + max_quality) // 2
            output = io.BytesIO()
            
            pdf_writer = PdfWriter()
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            
            # Apply compression settings
            pdf_writer.add_metadata({
                '/Compress': True,
                '/Quality': str(current_quality),
                '/ImageQuality': current_quality
            })
            
            pdf_writer.write(output)
            current_size = output.tell()
            
            if best_size is None or abs(current_size - target_bytes) < abs(best_size - target_bytes):
                best_quality = current_quality
                best_size = current_size
                best_output = output
            
            if current_size > target_bytes:
                max_quality = current_quality - 1
            else:
                min_quality = current_quality + 1
            
            if abs(current_size - target_bytes) <= 512:  # 0.5KB tolerance
                break
        
        if best_output is None:
            return None, False, "Failed to achieve target size"
        
        best_output.seek(0)
        actual_size = best_output.tell() // 1024
        return best_output, True, f"Compressed to {actual_size}KB (Quality: {best_quality}%)"
    
    except Exception as e:
        logging.error(f"PDF compression error: {str(e)}")
        return None, False, f"PDF compression failed: {str(e)}"

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/compress', methods=['POST'])
def compress_file():
    """Handle file compression requests."""
    try:
        # Validate file presence
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Get and validate target size
        try:
            target_size = float(request.form.get('targetSize', 100))
            if target_size <= 0:
                return jsonify({'error': 'Target size must be greater than 0'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid target size'}), 400
        
        # Process file based on type
        filename = secure_filename(file.filename)
        file_type = get_file_type(filename)
        
        if file_type == 'image':
            compressed, success, message = compress_image(file, target_size)
        elif file_type == 'document':
            compressed, success, message = compress_pdf(file, target_size)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        if not success or compressed is None:
            return jsonify({'error': message}), 400
        
        # Log successful compression
        logging.info(f"Successfully compressed {filename}: {message}")
        
        # Return compressed file
        return send_file(
            compressed,
            mimetype='image/jpeg' if file_type == 'image' else 'application/pdf',
            as_attachment=True,
            download_name=f'compressed_{filename}'
        )
        
    except Exception as e:
        logging.error(f"Compression request failed: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({'error': 'File is too large (max 16MB)'}), 413

@app.errorhandler(500)
def server_error(e):
    """Handle internal server errors."""
    logging.error(f"Server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
