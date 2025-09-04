# AI Image Analysis & Generation API

A serverless AI-powered image processing web application built with Flask that integrates with Google's Gemini AI API. The application provides three core functionalities: image analysis, image generation, and image editing capabilities.

## Features

- **🔍 Image Analysis**: Upload images or provide URLs to get detailed AI descriptions and optional object segmentation masks
- **🎨 Image Generation**: Generate high-quality images from text descriptions with various style presets
- **✏️ Image Editing**: Upload an image and describe modifications to create enhanced versions
- **📖 API Documentation**: Complete reference for all available endpoints and features

## Tech Stack

- **Backend**: Flask (Python)
- **AI Service**: Google Gemini AI API
- **Frontend**: HTML/CSS/JavaScript with Bootstrap 5
- **Deployment**: Vercel (Serverless)
- **Image Processing**: PIL (Pillow)

## Setup Instructions

### Prerequisites

1. Python 3.11 or higher
2. Google Gemini API key
3. Vercel account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. **Install dependencies**
   ```bash
   pip install flask google-genai pillow requests werkzeug gunicorn
   ```

3. **Set environment variables**
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"
   export SESSION_SECRET="your_secret_key_here"
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Deployment to Vercel

### Step 1: Prepare Your Project

1. Make sure all files are in your project root:
   - `app.py` (main application file)
   - `vercel.json` (Vercel configuration)
   - `templates/index.html` (HTML template)
   - `static/` directory (for generated images)

### Step 2: Install Vercel CLI

```bash
npm i -g vercel
```

### Step 3: Login to Vercel

```bash
vercel login
```

### Step 4: Set Environment Variables

In your Vercel dashboard or via CLI, set these environment variables:

```bash
vercel env add GEMINI_API_KEY
vercel env add SESSION_SECRET
```

When prompted, enter your actual API keys:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `SESSION_SECRET`: A random secret key for Flask sessions

### Step 5: Deploy

```bash
vercel
```

Follow the prompts to deploy your application. Vercel will automatically detect the Flask app and configure it as a serverless function.

## Getting API Keys

### Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key and set it as `GEMINI_API_KEY` environment variable

## 📚 Complete API Documentation

### Base URL
- **Local Development**: `http://localhost:5000`
- **Production**: `https://your-app.vercel.app`

### Authentication
All endpoints require a valid `GEMINI_API_KEY` to be set in environment variables. No API key authentication is required for client requests.

---

## 🔍 Image Analysis Endpoints

### 1. Analyze Base64 Image
**Endpoint**: `POST /analyze_base64`

**Description**: Analyze a Base64 encoded image and get AI-generated descriptions.

**Request Body**:
```json
{
  "image": "base64_encoded_image_string",
  "extract_masks": false
}
```

**Parameters**:
- `image` (string, required): Base64 encoded image data (without data URL prefix)
- `extract_masks` (boolean, optional): Extract object segmentation masks (default: false)

**Success Response** (200):
```json
{
  "status": "success",
  "analysis": "Detailed AI description of the image...",
  "segmentation_masks": []
}
```

**Error Response** (400/500):
```json
{
  "error": "Error message description"
}
```

**Example Usage**:
```javascript
const response = await fetch('/analyze_base64', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        image: "iVBORw0KGgoAAAANSUhEUgAA...", // Base64 data
        extract_masks: false
    })
});
const result = await response.json();
```

---

### 2. Analyze Image from URL
**Endpoint**: `POST /analyze_url`

**Description**: Analyze an image from a public URL.

**Request Body**:
```json
{
  "url": "https://example.com/image.jpg",
  "extract_masks": false
}
```

**Parameters**:
- `url` (string, required): Public URL of the image to analyze
- `extract_masks` (boolean, optional): Extract object segmentation masks (default: false)

**Success Response** (200):
```json
{
  "status": "success",
  "analysis": "Detailed AI description of the image...",
  "segmentation_masks": []
}
```

**Error Response** (400/500):
```json
{
  "error": "Error message description"
}
```

**Example Usage**:
```javascript
const response = await fetch('/analyze_url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        url: "https://example.com/sample-image.jpg",
        extract_masks: true
    })
});
```

---

## 🎨 Image Generation Endpoints

### 3. Generate Image from Text
**Endpoint**: `POST /generate_text_to_image`

**Description**: Generate images from text descriptions using AI.

**Request Body**:
```json
{
  "prompt": "A beautiful sunset over mountains",
  "style": "photorealistic",
  "aspect_ratio": "1:1"
}
```

**Parameters**:
- `prompt` (string, required): Text description of the image to generate
- `style` (string, optional): Style preset (default: "photorealistic")
  - Available styles: `photorealistic`, `cartoon`, `abstract`, `impressionistic`, `cyberpunk`, `anime`, `oil_painting`, `watercolor`, `sketch`, `digital_art`
- `aspect_ratio` (string, optional): Image aspect ratio (default: "1:1")
  - Available ratios: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`

**Success Response** (200):
```json
{
  "status": "success",
  "prompt": "A beautiful sunset over mountains",
  "generated_text": "AI response text about the generation",
  "generated_image": "base64_encoded_image_data",
  "saved_files": ["generated_image_20250904_123456_abc123.png"],
  "total_images": 1
}
```

**Error Response** (400/500):
```json
{
  "status": "error",
  "error": "Error message description"
}
```

**Example Usage**:
```javascript
const response = await fetch('/generate_text_to_image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        prompt: "A futuristic cityscape at night with neon lights",
        style: "cyberpunk",
        aspect_ratio: "16:9"
    })
});
```

---

### 4. Edit Image with AI
**Endpoint**: `POST /edit_image`

**Description**: Edit an existing image using AI based on text instructions.

**Request Body**:
```json
{
  "prompt": "Add a small wizard hat on the cat's head",
  "image": "base64_encoded_image_data",
  "style": "photorealistic",
  "aspect_ratio": "1:1",
  "edit_strength": 0.7
}
```

**Parameters**:
- `prompt` (string, required): Description of how to edit the image
- `image` (string, required): Base64 encoded original image
- `style` (string, optional): Style for the edited image (default: "photorealistic")
- `aspect_ratio` (string, optional): Aspect ratio for result (default: "1:1")
- `edit_strength` (float, optional): How much to change the original (0.0-1.0, default: 0.7)

**Success Response** (200):
```json
{
  "status": "success",
  "prompt": "Add a small wizard hat on the cat's head",
  "generated_text": "AI response about the edit",
  "generated_image": "base64_encoded_edited_image",
  "saved_files": ["edited_image_20250904_123456_def456.png"],
  "total_images": 1
}
```

**Error Response** (400/500):
```json
{
  "status": "error",
  "error": "Error message description"
}
```

**Example Usage**:
```javascript
const response = await fetch('/edit_image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        prompt: "Change the background to a starry night sky",
        image: "iVBORw0KGgoAAAANSUhEUgAA...", // Base64 original image
        style: "impressionistic",
        edit_strength: 0.8
    })
});
```

---

### 5. Compose Multiple Images
**Endpoint**: `POST /compose_images`

**Description**: Combine multiple images into one composition based on text instructions.

**Request Body**:
```json
{
  "prompt": "Combine these images to create a surreal landscape",
  "images": ["base64_image1", "base64_image2", "base64_image3"]
}
```

**Parameters**:
- `prompt` (string, required): Description of how to compose the images
- `images` (array, required): Array of base64 encoded images (minimum 2 images)

**Success Response** (200):
```json
{
  "status": "success",
  "prompt": "Combine these images to create a surreal landscape",
  "input_images_count": 3,
  "generated_text": "AI response about the composition",
  "generated_image": "base64_encoded_composed_image",
  "saved_files": ["composed_image_20250904_123456_ghi789.png"],
  "total_images": 1
}
```

**Error Response** (400/500):
```json
{
  "status": "error",
  "error": "Error message description"
}
```

**Example Usage**:
```javascript
const response = await fetch('/compose_images', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        prompt: "Create a collage showing the progression from day to night",
        images: [
            "iVBORw0KGgoAAAANSUhEUgAA...", // Day image
            "iVBORw0KGgoAAAANSUhEUgAA...", // Sunset image
            "iVBORw0KGgoAAAANSUhEUgAA..."  // Night image
        ]
    })
});
```

---

## 🔧 Utility Endpoints

### 6. Web Interface
**Endpoint**: `GET /`

**Description**: Serves the main web interface with tabbed navigation for all features.

**Response**: HTML page with interactive interface

---

### 7. Health Check
**Endpoint**: `GET /health`

**Description**: Check API health and service status.

**Success Response** (200):
```json
{
  "status": "healthy",
  "message": "AI Image API is running",
  "gemini_api": "available",
  "capabilities": {
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
}
```

---

### 8. API Documentation
**Endpoint**: `GET /api`

**Description**: Get complete API documentation in JSON format.

**Success Response** (200):
```json
{
  "message": "AI Image Analysis & Generation API",
  "version": "2.0",
  "description": "Complete AI-powered image processing with Google Gemini",
  "base_url": "https://your-domain.com",
  "endpoints": {
    "image_analysis": {...},
    "image_generation": {...},
    "utility": {...}
  },
  "features": [...]
}
```

---

## 🚨 Error Codes and Messages

### Common HTTP Status Codes
- **200**: Success
- **400**: Bad Request (missing parameters, invalid data)
- **500**: Internal Server Error (API issues, processing errors)

### Common Error Messages
- `"No image data provided"` - Missing image in request
- `"No prompt provided"` - Missing prompt for generation/editing
- `"No image URL provided"` - Missing URL for URL analysis
- `"At least 2 images are required for composition"` - Insufficient images for composition
- `"Invalid or missing Gemini API key"` - API key issues
- `"API quota exceeded or rate limit reached"` - Usage limits exceeded
- `"Permission denied"` - API key permissions issue

---

## 📋 Dependencies

Dependencies are managed through `pyproject.toml`. For Vercel deployment, all dependencies are automatically installed. For local development, install:

```bash
pip install flask google-genai pillow requests werkzeug gunicorn
```

**Core Dependencies**:
- `flask>=3.1.2` - Web framework
- `google-genai>=1.33.0` - Google Gemini AI client
- `pillow>=11.3.0` - Image processing
- `requests>=2.32.5` - HTTP requests
- `werkzeug>=3.1.3` - WSGI utilities
- `gunicorn>=23.0.0` - Production server

## Project Structure

```
├── app.py                 # Main Flask application
├── vercel.json           # Vercel deployment configuration
├── templates/
│   └── index.html        # Web interface template
├── static/
│   └── generated_images/ # Storage for generated images
├── README.md            # This file
└── pyproject.toml       # Python dependencies
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini AI API key | Yes |
| `SESSION_SECRET` | Secret key for Flask sessions | Yes |

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Verify your Gemini API key is correct
   - Check that the API key has proper permissions
   - Ensure environment variables are set correctly

2. **Image Generation Failing**
   - Check your API quota limits
   - Verify the prompt is appropriate and follows content guidelines
   - Try simpler prompts first

3. **Deployment Issues**
   - Ensure all required files are present
   - Check that environment variables are set in Vercel
   - Verify the vercel.json configuration is correct

### Support

For support and issues, please check:
1. The `/health` endpoint to verify API status
2. Browser console for client-side errors
3. Vercel function logs for server-side errors

## License

This project is open source and available under the [MIT License](LICENSE).