import os
from flask import Flask, render_template, request, send_from_directory, url_for, jsonify
from werkzeug.utils import secure_filename
from stylize_inference import perform_inference

app = Flask(__name__, template_folder='.', static_folder='static', static_url_path='/static')

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
MODEL_FOLDER = 'saved_models'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MODEL_FOLDER'] = MODEL_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)
os.makedirs('static/previews', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # List available models
    models = [f for f in os.listdir(MODEL_FOLDER) if f.endswith('.pth')]
    # Sort models alphabetically for consistent display
    models.sort()
    
    # Ensure we have our 4 expected models
    if not models:
        models = ['candy.pth', 'mosaic.pth', 'rain_princess.pth', 'udnie.pth']
    
    return render_template('index.html', models=models)

@app.route('/stylize', methods=['POST'])
def stylize():
    # Validate file upload
    if 'content_image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['content_image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate style selection
    style_model_name = request.form.get('style_model')
    if not style_model_name:
        return jsonify({'error': 'No style selected'}), 400
    
    # Process file
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        style_name = style_model_name.replace('.pth', '')
        output_filename = f"{base_name}_{style_name}_styled.jpg"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        model_path = os.path.join(app.config['MODEL_FOLDER'], style_model_name)
        
        # Check if model exists
        if not os.path.exists(model_path):
            return jsonify({'error': f'Model "{style_name}" not found on server. Please ensure models are downloaded.'}), 404

        try:
            # Perform style transfer
            perform_inference(input_path, model_path, output_path)
            
            # Return success with output URL
            return jsonify({
                'success': True,
                'output_url': url_for('get_output_file', filename=output_filename),
                'style_used': style_name
            })
            
        except Exception as e:
            return jsonify({'error': f'Style transfer failed: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Please upload JPG or PNG.'}), 400

@app.route('/outputs/<filename>')
def get_output_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

# Add CORS headers for better API compatibility
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

if __name__ == '__main__':
    print("=" * 60)
    print("Neural Style Transfer Web App")
    print("=" * 60)
    print(f"Available models: {len(os.listdir(MODEL_FOLDER))} found")
    for model in sorted([f for f in os.listdir(MODEL_FOLDER) if f.endswith('.pth')]):
        print(f"  - {model}")
    print("=" * 60)
    print("Server starting at http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000, host='0.0.0.0')

