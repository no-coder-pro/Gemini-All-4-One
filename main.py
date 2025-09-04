from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from PIL import Image, ImageDraw
import io
import base64
import json
import numpy as np
import os
import requests
import logging
import uuid
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.INFO)

def cleanup_generated_images(directory="static/generated_images/"):
    """
    Deletes all files in the specified directory.
    """
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                print(f"Deleted: {file_path}")
            elif os.path.isdir(file_path):
                # Optionally, you could add logic to remove subdirectories if needed
                pass
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

def restart_application():
    """
    Simulates an application restart by exiting the process.
    This relies on an external process manager (like Replit's) to restart the application.
    """
    logging.info("Initiating application restart for cache cleanup.")
    os._exit(0) # Force exit to trigger restart by external process manager

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Schedule image cleanup to run every 5 minutes
scheduler.add_job(cleanup_generated_images, 'interval', minutes=5, id='image_cleanup_job')
logging.info("Scheduled image cleanup to run every 5 minutes.")

# Schedule application restart to run every 24 hours
scheduler.add_job(restart_application, 'interval', hours=24, id='app_restart_job')
logging.info("Scheduled application restart to run every 24 hours.")

# Define available styles for image generation
AVAILABLE_STYLES = {
    "photorealistic": "photorealistic",
    "cartoon": "cartoon style",
    "abstract": "abstract art",
    "impressionistic": "impressionist painting",
    "cyberpunk": "cyberpunk art style",
    "anime": "anime style",
    "oil_painting": "oil painting",
    "watercolor": "watercolor painting",
    "sketch": "pencil sketch",
    "digital_art": "digital art"
}

# Define available aspect ratios with dimensions
AVAILABLE_RATIOS = {
    "1:1": {"desc": "square format", "width": 1024, "height": 1024},
    "4:3": {"desc": "standard landscape format", "width": 1024, "height": 768},
    "3:4": {"desc": "standard portrait format", "width": 768, "height": 1024},
    "16:9": {"desc": "landscape widescreen format", "width": 1024, "height": 576},
    "9:16": {"desc": "portrait vertical format", "width": 576, "height": 1024}
}

def resize_image_to_aspect_ratio(image_path, aspect_ratio):
    """Resize image to the specified aspect ratio"""
    try:
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        target_width = ratio_info["width"]
        target_height = ratio_info["height"]
        
        # Open and resize the image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate the aspect ratios
            img_aspect = img.width / img.height
            target_aspect = target_width / target_height
            
            if img_aspect > target_aspect:
                # Image is wider - crop width
                new_width = int(img.height * target_aspect)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            elif img_aspect < target_aspect:
                # Image is taller - crop height
                new_height = int(img.width / target_aspect)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))
            
            # Resize to target dimensions
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Save the resized image
            img.save(image_path, 'PNG', quality=95)
            
        logging.info(f"Image resized to {target_width}x{target_height} ({aspect_ratio})")
        return True
        
    except Exception as e:
        logging.error(f"Error resizing image: {str(e)}")
        return False

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Ensure static directory exists
os.makedirs('static/generated_images', exist_ok=True)

# Initialize Gemini client - only if API key exists
try:
    api_key = "AIzaSyB5TpGTpHOY1UFsggmpr25vgRdhMRTKfUA" # Hardcoded Gemini API Key
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = None
        logging.warning("GEMINI_API_KEY not found in environment variables")
except Exception as e:
    client = None
    logging.error(f"Failed to initialize Gemini client: {str(e)}")

# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 AI Image Analysis & Generation API</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.8em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .tabs {
            display: flex;
            margin-bottom: 30px;
            border-bottom: 3px solid #e9ecef;
        }
        .tab {
            padding: 15px 25px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            margin-right: 10px;
            font-weight: bold;
            transition: all 0.3s;
            border-radius: 10px 10px 0 0;
        }
        .tab.active {
            border-bottom-color: #007bff;
            background: linear-gradient(145deg, #f8f9fa, #e9ecef);
            color: #007bff;
        }
        .tab:hover {
            background: #f8f9fa;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .section {
            margin-bottom: 40px;
            padding: 25px;
            border: 2px solid #e1e5e9;
            border-radius: 15px;
            background: linear-gradient(145deg, #ffffff, #f8f9fa);
        }
        .section h2 {
            color: #495057;
            margin-top: 0;
            font-size: 1.6em;
            border-bottom: 2px solid #dee2e6;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #495057;
        }
        input[type="text"], input[type="url"], textarea, input[type="file"], select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ced4da;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input[type="text"]:focus, input[type="url"]:focus, textarea:focus, select:focus {
            border-color: #007bff;
            outline: none;
            box-shadow: 0 0 10px rgba(0,123,255,0.2);
        }
        textarea {
            resize: vertical;
            min-height: 100px;
        }
        button {
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            padding: 15px 25px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            margin-right: 10px;
            margin-bottom: 10px;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,123,255,0.3);
        }
        button:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }
        .checkbox-group {
            margin: 15px 0;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin-right: 8px;
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 12px;
            background-color: #f8f9fa;
            border: 2px solid #dee2e6;
        }
        .result h3 {
            margin-top: 0;
            color: #495057;
        }
        .result pre {
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
        }
        .error {
            background-color: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }
        .success {
            background-color: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }
        .loading {
            display: none;
            color: #007bff;
            font-style: italic;
            margin: 10px 0;
            font-weight: bold;
        }
        .generated-image, .preview-image {
            max-width: 100%;
            height: auto;
            margin: 15px 0;
            border: 3px solid #dee2e6;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .preview-image {
            max-width: 300px;
            max-height: 300px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        .feature-highlight {
            background: linear-gradient(45deg, #e3f2fd, #f3e5f5);
            border: 2px solid #2196f3;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .api-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            background: #28a745;
            color: white;
            font-weight: bold;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div class="api-status" id="apiStatus">🟢 API Ready</div>
    
    <div class="container">
        <h1>🤖 AI Image Analysis & Generation API</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('analysis')">🔍 Image Analysis</div>
            <div class="tab" onclick="switchTab('generation')">🎨 Image Generation</div>
            <div class="tab" onclick="switchTab('editing')">✏️ Image Editing</div>
            <div class="tab" onclick="switchTab('chat')">💬 Text Chat</div>
            <div class="tab" onclick="switchTab('docs')">📖 Documentation</div>
        </div>

        <!-- Image Analysis Tab -->
        <div id="analysis" class="tab-content active">
            <div class="feature-highlight">
                <h3>🔍 AI-Powered Image Analysis</h3>
                <p>Upload images or provide URLs to get detailed AI descriptions and optional object segmentation masks.</p>
            </div>
            
            <div class="grid">
                <div class="section">
                    <h2>📁 Upload Image File (Base64)</h2>
                    <div class="form-group">
                        <label for="analysisImageFile">Select Image File:</label>
                        <input type="file" id="analysisImageFile" accept="image/*">
                    </div>
                    <div class="checkbox-group">
                        <label>
                            <input type="checkbox" id="extractMasksFile"> Extract Segmentation Masks
                        </label>
                    </div>
                    <button onclick="analyzeImageFile()" id="analyzeFileBtn">🔍 Analyze Image</button>
                    <div class="loading" id="loadingAnalysisFile">Analyzing image...</div>
                    <div id="previewAnalysisFile"></div>
                    <div id="resultAnalysisFile"></div>
                </div>

                <div class="section">
                    <h2>🌐 Analyze Image from URL</h2>
                    <div class="form-group">
                        <label for="analysisImageUrl">Image URL:</label>
                        <input type="url" id="analysisImageUrl" placeholder="https://example.com/image.jpg" value="https://goo.gle/instrument-img">
                    </div>
                    <div class="checkbox-group">
                        <label>
                            <input type="checkbox" id="extractMasksUrl"> Extract Segmentation Masks
                        </label>
                    </div>
                    <button onclick="analyzeImageUrl()" id="analyzeUrlBtn">🔍 Analyze Image</button>
                    <div class="loading" id="loadingAnalysisUrl">Analyzing image...</div>
                    <div id="previewAnalysisUrl"></div>
                    <div id="resultAnalysisUrl"></div>
                </div>
            </div>
        </div>

        <!-- Image Generation Tab -->
        <div id="generation" class="tab-content">
            <div class="feature-highlight">
                <h3>🎨 AI Image Generation</h3>
                <p>Generate high-quality images from text descriptions with various style presets.</p>
            </div>
            
            <div class="section">
                <h2>✨ Text to Image Generation</h2>
                <div class="form-group">
                    <label for="textPrompt">Describe the image you want to generate:</label>
                    <textarea id="textPrompt" placeholder="A photorealistic close-up portrait of an elderly Japanese ceramicist with deep, sun-etched wrinkles and a warm, knowing smile..."></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="styleSelect">Style Preset (optional):</label>
                        <select id="styleSelect">
                            <option value="">Custom (use prompt as-is)</option>
                        <option value="photorealistic">Photorealistic</option>
                        <option value="illustration">Stylized Illustration</option>
                        <option value="sticker">Kawaii Sticker</option>
                        <option value="logo">Logo/Text Design</option>
                        <option value="product">Product Photography</option>
                        <option value="minimalist">Minimalist Design</option>
                        <option value="comic">Comic Book Style</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="aspectRatioSelect">📐 Aspect Ratio:</label>
                    <select id="aspectRatioSelect">
                        <option value="1:1">1:1 - Square (1024x1024)</option>
                        <option value="4:3">4:3 - Standard (1024x768)</option>
                        <option value="3:4">3:4 - Portrait (768x1024)</option>
                        <option value="16:9">16:9 - Widescreen (1024x576)</option>
                        <option value="9:16">9:16 - Vertical (576x1024)</option>
                    </select>
                </div>
            </div>
                <button onclick="generateImage()" id="generateBtn">🎨 Generate Image</button>
                <div class="loading" id="loadingGenerate">Generating image...</div>
                <div id="resultGenerate"></div>
            </div>

        </div>

        <!-- Image Editing Tab -->
        <div id="editing" class="tab-content">
            <div class="feature-highlight">
                <h3>✏️ AI Image Editing & Composition</h3>
                <p>Edit single images or combine multiple images with AI-powered prompts to create enhanced versions.</p>
            </div>
            
            <div class="grid">
                <div class="section">
                    <h2>🖼️ Single Image Editing</h2>
                    <div class="form-group">
                        <label for="editImage">Upload Image to Edit:</label>
                        <input type="file" id="editImage" accept="image/*">
                    </div>
                    <div class="form-group">
                        <label for="editPrompt">Describe how to edit the image:</label>
                        <textarea id="editPrompt" placeholder="Add a small, knitted wizard hat on the cat's head. Make it look like it's sitting comfortably and not falling off..."></textarea>
                    </div>
                    <div class="form-group">
                        <label for="aspectRatioEditSelect">📐 Aspect Ratio:</label>
                        <select id="aspectRatioEditSelect">
                            <option value="1:1">1:1 - Square (1024x1024)</option>
                            <option value="4:3">4:3 - Standard (1024x768)</option>
                            <option value="3:4">3:4 - Portrait (768x1024)</option>
                            <option value="16:9">16:9 - Widescreen (1024x576)</option>
                            <option value="9:16">9:16 - Vertical (576x1024)</option>
                        </select>
                    </div>
                    <button onclick="editSingleImage()" id="editBtn">✏️ Edit Image</button>
                    <div class="loading" id="loadingEdit">Editing image...</div>
                    <div id="previewEdit"></div>
                    <div id="resultEdit"></div>
                </div>

                <div class="section">
                    <h2>🎭 Multi-Image Composition</h2>
                    <div class="form-group">
                        <label for="multiImages">Upload Multiple Images (2 or more):</label>
                        <input type="file" id="multiImages" accept="image/*" multiple>
                    </div>
                    <div class="form-group">
                        <label for="composePrompt">Describe how to combine the images:</label>
                        <textarea id="composePrompt" placeholder="Combine these images to create a surreal landscape scene where the subjects from each image interact in a fantasy setting..."></textarea>
                    </div>
                    <button onclick="composeImages()" id="composeBtn">🎭 Compose Images</button>
                    <div class="loading" id="loadingCompose">Composing images...</div>
                    <div id="previewCompose"></div>
                    <div id="resultCompose"></div>
                </div>
            </div>
        </div>

        <!-- Text Chat Tab -->
        <div id="chat" class="tab-content">
            <div class="feature-highlight">
                <h3>💬 AI Text Chat</h3>
                <p>Ask questions and get intelligent answers from Gemini AI.</p>
            </div>
            
            <div class="section">
                <h2>🤖 Ask a Question</h2>
                <div class="form-group">
                    <label for="chatModel">Choose AI Model:</label>
                    <select id="chatModel">
                        <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Fast)</option>
                        <option value="gemini-2.5-flash" selected>Gemini 2.5 Flash (Faster)</option>
                        <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite (Fastest)</option>
                        <option value="gemini-2.5-pro">Gemini 2.5 Pro (Fast)</option>
                        <option value="gemini-1.5-flash">Gemini 1.5 Flash (Fastest)</option>
                        <option value="gemini-1.5-flash-8b">Gemini 1.5 Flash 8B (Fast)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="chatQuestion">Your Question:</label>
                    <textarea id="chatQuestion" placeholder="What is photosynthesis? How does machine learning work? Explain quantum physics..."></textarea>
                </div>
                <button onclick="askQuestion()" id="askBtn">💬 Ask Question</button>
                <div class="loading" id="loadingChat">Processing your question...</div>
                <div id="resultChat"></div>
            </div>
        </div>

        <!-- Documentation Tab -->
        <div id="docs" class="tab-content">
            <div class="feature-highlight">
                <h3>📖 API Documentation</h3>
                <p>Complete reference for all available endpoints and features.</p>
            </div>
            
            <div class="section">
                <h2>🏥 API Health Check</h2>
                <button onclick="checkHealth()">Check API Health</button>
                <div id="healthResult"></div>
            </div>
            
            <div class="section">
                <h2>📚 Available Endpoints</h2>
                <p><strong>Image Analysis:</strong></p>
                <ul>
                    <li><code>POST /analyze_base64</code> - Analyze Base64 encoded images</li>
                    <li><code>POST /analyze_url</code> - Analyze images from URLs</li>
                </ul>
                <p><strong>Text Chat:</strong></p>
                <ul>
                    <li><code>POST /ask</code> - Ask questions with multiple AI models
                        <br><small>Models: Gemini 2.0 Flash, 2.5 Flash, 2.5 Flash Lite, 2.5 Pro, 1.5 Flash, 1.5 Flash 8B</small>
                    </li>
                </ul>
                <p><strong>Image Generation:</strong></p>
                <ul>
                    <li><code>POST /generate_text_to_image</code> - Generate images from text</li>
                    <li><code>POST /edit_image</code> - Edit images with text prompts</li>
                    <li><code>POST /compose_images</code> - Compose multiple images</li>
                </ul>
                <p><strong>Utility:</strong></p>
                <ul>
                    <li><code>GET /health</code> - API health check</li>
                    <li><code>GET /api</code> - Complete API documentation</li>
                </ul>
                <p><a href="/api" target="_blank">View Full API Documentation</a></p>
            </div>
        </div>
    </div>

    <script>
        // Tab switching functionality
        function switchTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            // Add active class to clicked tab
            event.target.classList.add('active');
        }

        // Style presets mapping
        const stylePresets = {
            photorealistic: "A photorealistic, high-resolution image with professional photography lighting and composition. ",
            illustration: "A stylized digital illustration with bold colors and clean artwork. ",
            sticker: "A kawaii-style sticker design with bold outlines, bright colors, and transparent background. ",
            logo: "A modern, clean logo design with professional typography and minimalist aesthetic. ",
            product: "A high-quality product photography shot with studio lighting and professional composition. ",
            minimalist: "A minimalist design with significant negative space, clean lines, and subtle colors. ",
            comic: "A comic book style illustration with bold lines, dramatic lighting, and vibrant colors. "
        };

        // Convert file to base64
        function fileToBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result);
                reader.onerror = error => reject(error);
            });
        }

        // Display result with image support
        function displayResult(elementId, data, isError = false) {
            const resultDiv = document.getElementById(elementId);
            let html = `<div class="result ${isError ? 'error' : 'success'}">
                <h3>${isError ? 'Error' : 'Result'}</h3>`;
            
            if (!isError && data.generated_image) {
                html += `<img src="data:image/png;base64,${data.generated_image}" class="generated-image" alt="Generated Image">`;
            } else if (!isError && data.note) {
                html += `<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 10px 0; color: #856404;">
                    <strong>Note:</strong> ${data.note}
                </div>`;
            }
            
            html += `<pre>${JSON.stringify(data, null, 2)}</pre></div>`;
            resultDiv.innerHTML = html;
        }

        // Show loading state
        function showLoading(loadingId, buttonId, show) {
            document.getElementById(loadingId).style.display = show ? 'block' : 'none';
            document.getElementById(buttonId).disabled = show;
        }

        // Image Analysis Functions
        async function analyzeImageFile() {
            const fileInput = document.getElementById('analysisImageFile');
            const extractMasks = document.getElementById('extractMasksFile').checked;
            
            if (!fileInput.files[0]) {
                alert('Please select an image file');
                return;
            }

            showLoading('loadingAnalysisFile', 'analyzeFileBtn', true);

            try {
                const base64 = await fileToBase64(fileInput.files[0]);
                const base64Data = base64.split(',')[1];

                document.getElementById('previewAnalysisFile').innerHTML = `
                    <img src="${base64}" alt="Preview" class="preview-image">
                `;

                const response = await fetch('/analyze_base64', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image: base64Data,
                        extract_masks: extractMasks
                    })
                });

                const result = await response.json();
                displayResult('resultAnalysisFile', result, !response.ok);

            } catch (error) {
                displayResult('resultAnalysisFile', { error: error.message }, true);
            } finally {
                showLoading('loadingAnalysisFile', 'analyzeFileBtn', false);
            }
        }

        async function analyzeImageUrl() {
            const urlInput = document.getElementById('analysisImageUrl');
            const extractMasks = document.getElementById('extractMasksUrl').checked;
            
            if (!urlInput.value) {
                alert('Please enter an image URL');
                return;
            }

            showLoading('loadingAnalysisUrl', 'analyzeUrlBtn', true);

            try {
                document.getElementById('previewAnalysisUrl').innerHTML = `
                    <img src="${urlInput.value}" alt="Preview" class="preview-image" onerror="this.style.display='none'">
                `;

                const response = await fetch('/analyze_url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: urlInput.value,
                        extract_masks: extractMasks
                    })
                });

                const result = await response.json();
                displayResult('resultAnalysisUrl', result, !response.ok);

            } catch (error) {
                displayResult('resultAnalysisUrl', { error: error.message }, true);
            } finally {
                showLoading('loadingAnalysisUrl', 'analyzeUrlBtn', false);
            }
        }

        // Image Generation Functions
        async function generateImage() {
            const prompt = document.getElementById('textPrompt').value;
            const style = document.getElementById('styleSelect').value;
            const aspectRatio = document.getElementById('aspectRatioSelect').value;
            
            if (!prompt.trim()) {
                alert('Please enter a text prompt');
                return;
            }

            showLoading('loadingGenerate', 'generateBtn', true);

            try {
                const finalPrompt = style ? stylePresets[style] + prompt : prompt;
                
                const response = await fetch('/generate_text_to_image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        prompt: finalPrompt, 
                        aspect_ratio: aspectRatio 
                    })
                });

                const result = await response.json();
                displayResult('resultGenerate', result, !response.ok);

            } catch (error) {
                displayResult('resultGenerate', { error: error.message }, true);
            } finally {
                showLoading('loadingGenerate', 'generateBtn', false);
            }
        }

        async function editSingleImage() {
            const fileInput = document.getElementById('editImage');
            const prompt = document.getElementById('editPrompt').value;
            const aspectRatio = document.getElementById('aspectRatioEditSelect').value;
            
            if (!fileInput.files[0] || !prompt.trim()) {
                alert('Please select an image and enter an edit prompt');
                return;
            }

            showLoading('loadingEdit', 'editBtn', true);

            try {
                const base64 = await fileToBase64(fileInput.files[0]);
                const base64Data = base64.split(',')[1];

                document.getElementById('previewEdit').innerHTML = `
                    <img src="${base64}" alt="Original" class="preview-image">
                `;

                const response = await fetch('/edit_image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image: base64Data,
                        prompt: prompt,
                        aspect_ratio: aspectRatio
                    })
                });

                const result = await response.json();
                displayResult('resultEdit', result, !response.ok);

            } catch (error) {
                displayResult('resultEdit', { error: error.message }, true);
            } finally {
                showLoading('loadingEdit', 'editBtn', false);
            }
        }

        async function composeImages() {
            const fileInput = document.getElementById('multiImages');
            const prompt = document.getElementById('composePrompt').value;
            
            if (!fileInput.files.length || fileInput.files.length < 2 || !prompt.trim()) {
                alert('Please select at least 2 images and enter a composition prompt');
                return;
            }

            showLoading('loadingCompose', 'composeBtn', true);

            try {
                const images = [];
                let previewHtml = '';
                
                for (let file of fileInput.files) {
                    const base64 = await fileToBase64(file);
                    const base64Data = base64.split(',')[1];
                    images.push(base64Data);
                    previewHtml += `<img src="${base64}" alt="Input" class="preview-image" style="max-width: 150px; margin: 5px;">`;
                }

                document.getElementById('previewCompose').innerHTML = previewHtml;

                const response = await fetch('/compose_images', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        images: images,
                        prompt: prompt
                    })
                });

                const result = await response.json();
                displayResult('resultCompose', result, !response.ok);

            } catch (error) {
                displayResult('resultCompose', { error: error.message }, true);
            } finally {
                showLoading('loadingCompose', 'composeBtn', false);
            }
        }

        // Text Chat Function
        async function askQuestion() {
            const question = document.getElementById('chatQuestion').value;
            const model = document.getElementById('chatModel').value;
            
            if (!question.trim()) {
                alert('Please enter a question');
                return;
            }

            showLoading('loadingChat', 'askBtn', true);

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: question,
                        model: model
                    })
                });

                const result = await response.json();
                
                if (response.ok) {
                    displayChatResult('resultChat', result);
                } else {
                    displayResult('resultChat', result, true);
                }

            } catch (error) {
                displayResult('resultChat', { error: error.message }, true);
            } finally {
                showLoading('loadingChat', 'askBtn', false);
            }
        }

        // Display chat result with formatted answer
        function displayChatResult(elementId, data) {
            const resultDiv = document.getElementById(elementId);
            const formattedAnswer = data.answer.split('\\n').join('<br>');
            let html = `<div class="result success">
                <h3>💬 Answer</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #007bff;">
                    <strong>Q:</strong> ${data.question}
                </div>
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #28a745;">
                    <strong>A:</strong> ${formattedAnswer}
                </div>`;
            
            if (data.model_used) {
                html += `<div style="background: #fff3cd; padding: 10px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #ffc107; font-size: 0.9em;">
                    <strong>Model:</strong> ${data.model_used}
                </div>`;
            }
            
            html += `</div>`;
            resultDiv.innerHTML = html;
        }

        async function checkHealth() {
            try {
                const response = await fetch('/health');
                const result = await response.json();
                displayResult('healthResult', result, !response.ok);
            } catch (error) {
                displayResult('healthResult', { error: error.message }, true);
            }
        }

        // Initialize API status
        checkHealth().then(() => {
            document.getElementById('apiStatus').textContent = '🟢 API Ready';
        }).catch(() => {
            document.getElementById('apiStatus').textContent = '🔴 API Error';
            document.getElementById('apiStatus').style.background = '#dc3545';
        });
    </script>
</body>
</html>"""

def analyze_image_with_genai(image):
    """Analyze image using Google Generative AI"""
    if not client:
        return "Error: Gemini API client not initialized. Please check your GEMINI_API_KEY."
    
    try:
        # Convert PIL image to bytes for the new API
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Use the new google.genai client API
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=img_byte_arr,
                    mime_type="image/png",
                ),
                "What is this image? Provide a detailed description."
            ]
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    return part.text
        
        return "Unable to analyze the image."
        
    except Exception as e:
        logging.error(f"Error in analyze_image_with_genai: {str(e)}")
        return f"Error analyzing image: {str(e)}"

def extract_segmentation_masks(image):
    """Extract segmentation masks from image"""
    if not client:
        return {"error": "Gemini API client not initialized"}
    
    try:
        # Placeholder for mask extraction - this would require specific Gemini features
        return []
        
    except Exception as e:
        return {"error": f"Failed to extract segmentation masks: {str(e)}"}

def generate_image_from_text(prompt, style="photorealistic", aspect_ratio="1:1"):
    """Generate image from text prompt using Gemini API"""
    if not client:
        return {
            'status': 'error',
            'error': 'Gemini API client not initialized. Please check your GEMINI_API_KEY environment variable.'
        }
    
    try:
        # Get style and ratio descriptions
        style_desc = AVAILABLE_STYLES.get(style, AVAILABLE_STYLES["photorealistic"])
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        ratio_desc = ratio_info["desc"]
        
        # Enhanced prompt engineering for higher quality
        quality_modifiers = "high resolution, sharp focus, highly detailed, masterpiece, best quality, ultra-detailed, 8k, HDR"
        enhanced_prompt = f"Create a {style_desc} image: {prompt}. {ratio_desc}. {quality_modifiers}. Professional lighting and composition."
        
        logging.info(f"Generating image with prompt: {prompt}")
        logging.info(f"Enhanced prompt: {enhanced_prompt}")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"generated_image_{timestamp}_{unique_id}.png"
        image_path = os.path.join("static", "generated_images", image_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        # Call Gemini API for image generation
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[enhanced_prompt],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        if not response.candidates:
            logging.error("No candidates returned from Gemini API")
            return {
                'status': 'error',
                'error': 'No image generated by the API. Please try a different prompt.'
            }
        
        # Process the response
        content = response.candidates[0].content
        if not content or not content.parts:
            logging.error("No content or parts in API response")
            return {
                'status': 'error',
                'error': 'Invalid response from image generation API'
            }
        
        image_saved = False
        response_text = None
        
        # Extract image data and text from response
        for part in content.parts:
            if part.text:
                response_text = part.text
                logging.info(f"API response text: {part.text}")
            elif part.inline_data and part.inline_data.data:
                try:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    logging.info(f"Image saved successfully at: {image_path}")
                    
                    # Resize image to correct aspect ratio
                    if resize_image_to_aspect_ratio(image_path, aspect_ratio):
                        logging.info(f"Image resized to {aspect_ratio} aspect ratio")
                        
                except Exception as file_error:
                    logging.error(f"Error saving image file: {file_error}")
                    return {
                        'status': 'error',
                        'error': f'Failed to save generated image: {str(file_error)}'
                    }
        
        if not image_saved:
            logging.error("No image data found in API response")
            return {
                'status': 'error',
                'error': 'No image data received from the API. The model may not support this prompt.'
            }
        
        return {
            'status': 'success',
            'image_path': image_path,
            'response_text': response_text,
            'filename': image_filename
        }
        
    except Exception as e:
        logging.error(f"Error in generate_image_from_text: {str(e)}")
        
        # Provide more specific error messages
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded or rate limit reached. Please try again later."
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        else:
            error_msg = f"Failed to generate image: {str(e)}"
        
        return {
            'status': 'error',
            'error': error_msg
        }

def edit_image_with_prompt(image_data, edit_prompt, style="photorealistic", aspect_ratio="1:1", edit_strength=0.7):
    """Edit an uploaded image using text prompt with Gemini API"""
    if not client:
        return {
            'status': 'error',
            'error': 'Gemini API client not initialized. Please check your GEMINI_API_KEY environment variable.'
        }
    
    try:
        # Get style and ratio descriptions
        style_desc = AVAILABLE_STYLES.get(style, AVAILABLE_STYLES["photorealistic"])
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        ratio_desc = ratio_info["desc"]
        
        # Enhanced prompt for better editing results
        quality_modifiers = "high resolution, sharp focus, highly detailed, masterpiece quality"
        enhanced_prompt = f"Modify this image by: {edit_prompt}. Style: {style_desc}. Format: {ratio_desc}. Maintain {quality_modifiers} and preserve the original composition while making the requested changes."
        
        logging.info(f"Starting image editing with prompt: {edit_prompt}")
        
        # Generate unique filename for edited image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"edited_image_{timestamp}_{unique_id}.png"
        image_path = os.path.join("static", "generated_images", image_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        # Call Gemini API for image editing
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[
                types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/png",
                ),
                enhanced_prompt
            ],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        if not response.candidates:
            logging.error("No candidates returned from Gemini API for image editing")
            return {
                'status': 'error',
                'error': 'No edited image generated by the API. Please try a different prompt or image.'
            }
        
        # Process the response
        content = response.candidates[0].content
        if not content or not content.parts:
            logging.error("No content or parts in API response for image editing")
            return {
                'status': 'error',
                'error': 'Invalid response from image editing API'
            }
        
        image_saved = False
        response_text = None
        
        # Extract image data and text from response
        for part in content.parts:
            if part.text:
                response_text = part.text
                logging.info(f"API response text: {part.text}")
            elif part.inline_data and part.inline_data.data:
                try:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    logging.info(f"Edited image saved successfully at: {image_path}")
                    
                    # Resize image to correct aspect ratio
                    if resize_image_to_aspect_ratio(image_path, aspect_ratio):
                        logging.info(f"Edited image resized to {aspect_ratio} aspect ratio")
                        
                except Exception as file_error:
                    logging.error(f"Error saving edited image file: {file_error}")
                    return {
                        'status': 'error',
                        'error': f'Failed to save edited image: {str(file_error)}'
                    }
        
        if not image_saved:
            logging.error("No image data found in API response for editing")
            return {
                'status': 'error',
                'error': 'No edited image data received from the API. The model may not support this edit.'
            }
        
        return {
            'status': 'success',
            'image_path': image_path,
            'response_text': response_text,
            'filename': image_filename
        }
        
    except Exception as e:
        logging.error(f"Error in edit_image_with_prompt: {str(e)}")
        
        # Provide more specific error messages
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded or rate limit reached. Please try again later."
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        else:
            error_msg = f"Failed to edit image: {str(e)}"
        
        return {
            'status': 'error',
            'error': error_msg
        }

def compose_images_with_prompt(images_data, composition_prompt, style="photorealistic", aspect_ratio="1:1"):
    """
    Compose multiple images into one using text prompt with Gemini API
    
    Args:
        images_data (list): List of image data (bytes) to compose
        composition_prompt (str): The text prompt describing how to compose the images
        style (str): The artistic style for the composed image (default: "photorealistic")
        aspect_ratio (str): The aspect ratio for the composed image (default: "1:1")
        
    Returns:
        dict: Result containing status, image_path or error message
    """
    if not client:
        return {
            'status': 'error',
            'error': 'Gemini API client not initialized. Please check your GEMINI_API_KEY environment variable.'
        }
    
    try:
        # Get style and ratio descriptions
        style_desc = AVAILABLE_STYLES.get(style, AVAILABLE_STYLES["photorealistic"])
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        ratio_desc = ratio_info["desc"]
        
        # Enhanced prompt for better composition results
        quality_modifiers = "high resolution, sharp focus, highly detailed, masterpiece quality"
        enhanced_prompt = f"Compose and combine these {len(images_data)} images to create: {composition_prompt}. Style: {style_desc}. Format: {ratio_desc}. Create a cohesive composition with {quality_modifiers} that seamlessly blends the input images according to the description."
        
        logging.info(f"Starting image composition with prompt: {composition_prompt}")
        logging.info(f"Number of input images: {len(images_data)}")
        logging.info(f"Style: {style} ({style_desc})")
        
        # Generate unique filename for composed image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"composed_image_{timestamp}_{unique_id}.png"
        image_path = os.path.join("static", "generated_images", image_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        # Prepare content for Gemini API - include all images and the prompt
        contents = []
        
        # Add all images as parts
        for i, image_data in enumerate(images_data):
            contents.append(
                types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/png",
                )
            )
        
        # Add the composition prompt
        contents.append(enhanced_prompt)
        
        # Call Gemini API for image composition
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        if not response.candidates:
            logging.error("No candidates returned from Gemini API for image composition")
            return {
                'status': 'error',
                'error': 'No composed image generated by the API. Please try a different prompt or images.'
            }
        
        # Process the response
        content = response.candidates[0].content
        if not content or not content.parts:
            logging.error("No content or parts in API response for image composition")
            return {
                'status': 'error',
                'error': 'Invalid response from image composition API'
            }
        
        image_saved = False
        response_text = None
        
        # Extract image data and text from response
        for part in content.parts:
            if part.text:
                response_text = part.text
                logging.info(f"API response text: {part.text}")
            elif part.inline_data and part.inline_data.data:
                try:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    logging.info(f"Composed image saved successfully at: {image_path}")
                    
                    # Resize image to correct aspect ratio
                    if resize_image_to_aspect_ratio(image_path, aspect_ratio):
                        logging.info(f"Composed image resized to {aspect_ratio} aspect ratio")
                        
                except Exception as file_error:
                    logging.error(f"Error saving composed image file: {file_error}")
                    return {
                        'status': 'error',
                        'error': f'Failed to save composed image: {str(file_error)}'
                    }
        
        if not image_saved:
            logging.error("No image data found in API response for composition")
            return {
                'status': 'error',
                'error': 'No composed image data received from the API. The model may not support this composition.'
            }
        
        return {
            'status': 'success',
            'image_path': image_path,
            'filename': image_filename,
            'response_text': response_text
        }
        
    except Exception as e:
        logging.error(f"Error in compose_images_with_prompt: {str(e)}")
        
        # Provide more specific error messages
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded or rate limit reached. Please try again later."
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        else:
            error_msg = f"Failed to compose images: {str(e)}"
        
        return {
            'status': 'error',
            'error': error_msg
        }

# Routes
@app.route('/', methods=['GET'])
def home():
    """Unified interface for all AI image operations"""
    return HTML_TEMPLATE

# Image Analysis Endpoints
@app.route('/analyze_base64', methods=['POST'])
def analyze_base64_image():
    """Endpoint for analyzing Base64 encoded images"""
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        base64_image = data['image']
        if base64_image.startswith('data:image'):
            base64_image = base64_image.split(',')[1]
        
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        analysis = analyze_image_with_genai(image)
        
        segmentation_results = []
        if data.get('extract_masks', False):
            segmentation_results = extract_segmentation_masks(image)
        
        return jsonify({
            "status": "success",
            "analysis": analysis,
            "segmentation_masks": segmentation_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_url', methods=['POST'])
def analyze_url_image():
    """Endpoint for analyzing images from URLs"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({"error": "No image URL provided"}), 400
        
        image_url = data['url']
        response = requests.get(image_url)
        response.raise_for_status()
        
        image = Image.open(io.BytesIO(response.content))
        analysis = analyze_image_with_genai(image)
        
        segmentation_results = []
        if data.get('extract_masks', False):
            segmentation_results = extract_segmentation_masks(image)
        
        return jsonify({
            "status": "success",
            "analysis": analysis,
            "segmentation_masks": segmentation_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Image Generation Endpoints
@app.route('/generate_text_to_image', methods=['POST'])
def generate_text_to_image():
    """Generate image from text prompt"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "No prompt provided"}), 400
        
        prompt = data['prompt']
        style = data.get('style', 'photorealistic')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        
        logging.info(f"Generating image for prompt: {prompt}")
        
        # Use the working image generation function
        result = generate_image_from_text(prompt, style, aspect_ratio)
        
        if result['status'] == 'success':
            # Read the image file and convert to base64 for compatibility
            with open(result['image_path'], 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return jsonify({
                "status": "success",
                "prompt": prompt,
                "generated_text": result.get('response_text', ''),
                "generated_image": image_base64,
                "saved_files": [result['filename']],
                "total_images": 1
            })
        else:
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Error in generate_text_to_image endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/edit_image', methods=['POST'])
def edit_image():
    """Edit image based on text prompt"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data or 'image' not in data:
            return jsonify({"error": "Prompt and image are required"}), 400
        
        prompt = data['prompt']
        base64_image = data['image']
        style = data.get('style', 'photorealistic')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        edit_strength = data.get('edit_strength', 0.7)
        
        # Decode the base64 image
        image_data = base64.b64decode(base64_image)
        
        logging.info(f"Editing image with prompt: {prompt}")
        
        # Use the working image editing function
        result = edit_image_with_prompt(image_data, prompt, style, aspect_ratio, edit_strength)
        
        if result['status'] == 'success':
            # Read the image file and convert to base64 for compatibility
            with open(result['image_path'], 'rb') as f:
                edited_image_data = f.read()
            image_base64 = base64.b64encode(edited_image_data).decode('utf-8')
            
            return jsonify({
                "status": "success",
                "prompt": prompt,
                "generated_text": result.get('response_text', ''),
                "generated_image": image_base64,
                "saved_files": [result['filename']],
                "total_images": 1
            })
        else:
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Error in edit_image endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/compose_images', methods=['POST'])
def compose_images():
    """Compose multiple images into one based on text prompt"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data or 'images' not in data:
            return jsonify({"error": "Prompt and images are required"}), 400
        
        prompt = data['prompt']
        base64_images = data['images']
        style = data.get('style', 'photorealistic')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        
        if len(base64_images) < 2:
            return jsonify({"error": "At least 2 images are required for composition"}), 400
        
        # Decode all base64 images to bytes
        images_data = []
        for i, base64_image in enumerate(base64_images):
            try:
                # Remove data URL prefix if present
                if base64_image.startswith('data:image'):
                    base64_image = base64_image.split(',')[1]
                
                image_data = base64.b64decode(base64_image)
                images_data.append(image_data)
            except Exception as decode_error:
                return jsonify({
                    "error": f"Failed to decode image {i+1}: {str(decode_error)}"
                }), 400
        
        logging.info(f"Composing {len(images_data)} images with prompt: {prompt}")
        
        # Use the composition function
        result = compose_images_with_prompt(images_data, prompt, style, aspect_ratio)
        
        if result['status'] == 'success':
            # Read the composed image file and convert to base64 for compatibility
            with open(result['image_path'], 'rb') as f:
                composed_image_data = f.read()
            image_base64 = base64.b64encode(composed_image_data).decode('utf-8')
            
            return jsonify({
                "status": "success",
                "prompt": prompt,
                "input_images_count": len(base64_images),
                "generated_text": result.get('response_text', ''),
                "generated_image": image_base64,
                "saved_files": [result['filename']],
                "total_images": 1
            })
        else:
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 500
        
    except Exception as e:
        logging.error(f"Error in compose_images endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    """Answer text questions using Gemini AI with model selection"""
    try:
        if not client:
            return jsonify({
                "error": "Gemini API client not initialized. Please check your GEMINI_API_KEY."
            }), 503

        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                "error": "Please provide a 'question' in the request body."
            }), 400
        
        user_question = data['question'].strip()
        selected_model = data.get('model', 'gemini-2.5-flash')  # Default to 2.5 Flash
        
        if not user_question:
            return jsonify({
                "error": "Question cannot be empty."
            }), 400
        
        # Validate model selection
        available_models = [
            'gemini-2.0-flash-exp',
            'gemini-2.5-flash', 
            'gemini-2.5-flash-lite',
            'gemini-2.5-pro',
            'gemini-1.5-flash',
            'gemini-1.5-flash-8b'
        ]
        
        if selected_model not in available_models:
            selected_model = 'gemini-2.5-flash'  # Fallback to default
        
        logging.info(f"Processing text question: {user_question}")
        logging.info(f"Using model: {selected_model}")
        
        # Use selected Gemini model for text-based question answering
        response = client.models.generate_content(
            model=selected_model,
            contents=user_question
        )
        
        if not response or not response.text:
            return jsonify({
                "error": "No response generated. Please try rephrasing your question."
            }), 500
        
        reply_text = response.text
        logging.info(f"Generated reply: {reply_text[:100]}...")
        
        return jsonify({
            "status": "success",
            "question": user_question,
            "answer": reply_text,
            "model_used": selected_model
        })
        
    except Exception as e:
        logging.error(f"Error in ask_question endpoint: {str(e)}")
        
        # Provide specific error messages
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded. Please try again later."
        elif "permission" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        elif "not found" in str(e).lower() or "invalid" in str(e).lower():
            error_msg = f"Model not available. Please try a different model."
        else:
            error_msg = f"An error occurred: {str(e)}"
        
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    api_status = "available" if client else "unavailable"
    return jsonify({
        "status": "healthy", 
        "message": "AI Image & Text API is running",
        "gemini_api": api_status,
        "capabilities": {
            "text_qa": [
                "natural language questions",
                "conversational responses",
                "general knowledge"
            ],
            "image_analysis": [
                "detailed descriptions",
                "object segmentation",
                "base64 and URL support"
            ],
            "image_generation": [
                "text-to-image generation",
                "image editing",
                "multi-image composition",
                "style presets"
            ]
        },
        "models": ["gemini-1.5-flash", "gemini-2.0-flash-preview-image-generation"]
    })

@app.route('/api', methods=['GET'])
def api_docs():
    """Complete API documentation"""
    return jsonify({
        "message": "AI Image Analysis & Generation API",
        "version": "2.0",
        "description": "Complete AI-powered image processing with Google Gemini",
        "base_url": request.host_url,
        "endpoints": {
            "image_analysis": {
                "/analyze_base64": {
                    "method": "POST",
                    "description": "Analyze Base64 encoded images",
                    "payload": {
                        "image": "base64_encoded_image_string (required)",
                        "extract_masks": "boolean (optional)"
                    }
                },
                "/analyze_url": {
                    "method": "POST",
                    "description": "Analyze images from URLs",
                    "payload": {
                        "url": "image_url_string (required)",
                        "extract_masks": "boolean (optional)"
                    }
                }
            },
            "image_generation": {
                "/generate_text_to_image": {
                    "method": "POST",
                    "description": "Generate images from text prompts",
                    "payload": {
                        "prompt": "text_description (required)"
                    }
                },
                "/edit_image": {
                    "method": "POST",
                    "description": "Edit images using text prompts",
                    "payload": {
                        "prompt": "edit_description (required)",
                        "image": "base64_encoded_image (required)"
                    }
                },
                "/compose_images": {
                    "method": "POST",
                    "description": "Compose multiple images",
                    "payload": {
                        "prompt": "composition_description (required)",
                        "images": "array_of_base64_images (required, min 2)"
                    }
                }
            },
            "utility": {
                "/": {
                    "method": "GET",
                    "description": "Web interface"
                },
                "/health": {
                    "method": "GET",
                    "description": "API health check"
                },
                "/api": {
                    "method": "GET",
                    "description": "This documentation"
                }
            }
        },
        "features": [
            "Image Analysis with AI descriptions",
            "Object Segmentation with masks",
            "Text-to-Image Generation",
            "AI-powered Image Editing",
            "Multi-Image Composition",
            "Style Presets and Templates",
            "Base64 and URL support",
            "Real-time processing"
        ]
    })

# For Vercel serverless deployment
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
