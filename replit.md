# AI Image Analysis & Generation API

## Overview

This is a serverless AI-powered image processing web application built with Flask that integrates with Google's Gemini AI API. The application provides three core functionalities: image analysis (with optional object segmentation), image generation from text descriptions, and image editing through natural language instructions. The system is designed as a RESTful API with a web interface for easy interaction and testing.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask-based Python web application with serverless deployment architecture
- **API Design**: RESTful endpoints following standard HTTP conventions for image processing operations
- **Error Handling**: Comprehensive logging and error response system for debugging and monitoring
- **Request Processing**: Supports both file uploads and URL-based image inputs with proper validation

### AI Integration
- **Primary AI Service**: Google Gemini AI API for all image processing tasks
- **Multi-modal Capabilities**: Leverages Gemini's vision and generation models for analysis, creation, and editing
- **Style System**: Predefined style presets (photorealistic, cartoon, abstract, etc.) and aspect ratio options for consistent image generation
- **Prompt Engineering**: Structured prompts for different use cases (analysis, generation, editing)

### Frontend Architecture
- **Technology Stack**: HTML/CSS/JavaScript with Bootstrap 5 for responsive design
- **User Interface**: Tab-based interface separating different functionalities (analysis, generation, editing)
- **Image Handling**: Client-side image preview and base64 encoding for API communication
- **Real-time Feedback**: Loading states and progress indicators for long-running AI operations

### Data Flow
- **Stateless Design**: No persistent data storage, all operations are request-response based
- **Image Processing Pipeline**: Upload → Validation → AI Processing → Response formatting → Client display
- **Memory Management**: PIL (Pillow) for image manipulation and format conversion in memory

### Security & Configuration
- **Environment Variables**: API keys and secrets managed through environment configuration
- **Session Management**: Flask sessions with configurable secret keys
- **Proxy Handling**: ProxyFix middleware for proper header handling in serverless environments

## External Dependencies

### Core AI Services
- **Google Gemini AI API**: Primary service for image analysis, generation, and editing capabilities
- **API Authentication**: Requires GEMINI_API_KEY environment variable for service access

### Python Libraries
- **Flask**: Web framework for API endpoints and request handling
- **google-genai**: Official Google Generative AI client library
- **PIL (Pillow)**: Image processing and manipulation library
- **requests**: HTTP client for external image URL fetching
- **werkzeug**: WSGI utilities and middleware support
- **gunicorn**: WSGI HTTP server for production deployment

### Deployment Platform
- **Vercel**: Serverless deployment platform with Python runtime support
- **Configuration**: Custom vercel.json with environment variable management and function timeout settings
- **Static Assets**: Local file system for temporary image storage during processing

### Development Tools
- **Logging**: Python's built-in logging module for application monitoring
- **Environment Management**: OS environment variables for configuration management
- **Error Handling**: Comprehensive exception handling for external service failures