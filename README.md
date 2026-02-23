# DeepSeek-OCR2: Dockerized PDF to Markdown API

A powerful OCR solution that converts PDF documents to Markdown format using **DeepSeek-OCR2** with a FastAPI backend. This project provides a production-ready Dockerized environment for high-performance OCR using vLLM.

## ⚠️ Important: How PDF Processing Works

**The DeepSeek OCR2 model does NOT accept PDF files directly.** PDFs are automatically converted to images (one per page) before being processed by the vision model. For a detailed technical explanation of this workflow, see [PDF_PROCESSING_WORKFLOW.md](./PDF_PROCESSING_WORKFLOW.md).

**Quick Summary:**
- PDF pages are rendered as images using PyMuPDF at 144 DPI
- Each page image is then processed by the DeepSeek OCR2 vision model
- This is a requirement of how vision-language models work - they need pixel data, not document structure

---

## 🚀 Quick Start

### 1. Download Model Weights

Create a directory for model weights and download the DeepSeek-OCR2 model:

```bash
# Create models directory
mkdir -p models/deepseek-ai/

# Download using Hugging Face CLI
pip install huggingface_hub
huggingface-cli download deepseek-ai/DeepSeek-OCR2 --local-dir models/deepseek-ai/DeepSeek-OCR2

# IMPORTANT: Remove .git folder inside models to save space (approx 6GB)
rm -rf models/deepseek-ai/DeepSeek-OCR2/.git
```

### 2. Build and Run the Docker Container

The model weights are baked into the image for portability.

#### Build for AMD64 (Standard GPU Servers)

```bash
docker buildx build --platform linux/amd64 -t shrey2003/deepseek-ocr2-dockerized:latest --load .
```

#### Build for ARM64/aarch64 (Apple Silicon, ARM Servers)

```bash
# Use the dedicated ARM64 build script
chmod +x build-arm64.sh
./build-arm64.sh
```

**⚠️ Common ARM64 Build Issues:**
- If you see "start_server.py: not found", make sure you have the latest code
- If build context is large (>10GB), ensure models/.git folder is removed
- See [ARM64_TROUBLESHOOTING.md](./ARM64_TROUBLESHOOTING.md) for detailed solutions

#### Build for Both AMD64 and ARM64 (Multi-Architecture)

```bash
# Use the multi-architecture build script
chmod +x build-multi-arch.sh
./build-multi-arch.sh
```

**📖 For detailed multi-architecture build instructions, see [MULTI_ARCH_BUILD.md](./MULTI_ARCH_BUILD.md)**

#### Start the service

```bash
docker-compose up -d
```

### 3. Verify Installation

```bash
curl http://localhost:8000/health
```

---

## 📋 Prerequisites

### Hardware Requirements
- **NVIDIA GPU** with CUDA 11.8+ support
- **GPU Memory**: Minimum 16GB VRAM (DeepSeek-OCR2 requires more memory than v1)
- **System RAM**: Minimum 32GB (recommended: 64GB+)
- **Storage**: 60GB+ free space for model and containers

---

## 🔌 REST API Usage

### API Endpoints

#### Process PDF
```bash
curl -X POST "http://localhost:8000/ocr/pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_document.pdf"
```

#### Process Image
```bash
curl -X POST "http://localhost:8000/ocr/image" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_image.jpg"
```

#### Custom Prompt
```bash
curl -X POST "http://localhost:8000/ocr/pdf" \
  -F "file=@your_document.pdf" \
  -F "prompt=<image>\nExtract all tables and format as CSV."
```

---

## ⚙️ Configuration & Patches

### Custom Patches for DeepSeek-OCR2

This project includes critical patches to make DeepSeek-OCR2 work reliably with modern vLLM and FastAPI. These are automatically applied during the Docker build.

### 1. Model Architecture & Registration
*   **DeepSeek-OCR2 Integration**: Migrated the backend from the v1 architecture to the new `DeepseekOCR2ForCausalLM` architecture.
*   **vLLM Model Registry**: Manually registered the `DeepSeek-OCR2` class in start_server.py using `ModelRegistry.register_model`, ensuring the vLLM engine recognizes the new model's visual causal flow.

### 2. Resolution & Vision Patch (Critical)
*   **768px Force**: DeepSeek-OCR2 is optimized for exactly **768x768** image inputs. The original code often defaulted to 640px, causing "UnboundLocalError" or vision token mismatches. We updated custom_config.py and the processor to strictly enforce 768px.
*   **Processor Patch**: Created custom_image_process_ocr2.py to fix a bug in the vendor's library where `tokenize_with_images()` did not accept a custom `prompt` argument. This patch is automatically injected into the container during the build.

### 3. Docker Optimization
*   **Weights Embedding**: Transitioned from using Docker volumes to **embedding the model weights** directly into the image (`COPY models/ /app/models/`). This makes the image fully portable and "plug-and-play."
*   **Size Reduction**: Optimized the image size by fixing .dockerignore and providing instructions to strip the **6.3GB .git folder** from the model weights before building.
*   **Architecture Locking**: Configured the build to target `linux/amd64`, ensuring compatibility with NVIDIA GPU servers

### 4. Code & Configuration Fixes
*   **Path Correction**: Fixed a bug where `MODEL_PATH` was defaulting to a Hugging Face repo ID (causing 401 errors); it now defaults to the absolute internal path `/app/models/deepseek-ai/DeepSeek-OCR2`.
*   **FastAPI Endpoints**: Updated start_server.py to handle OCR2-specific processor initialization, allowing for dynamic prompt passing (e.g., swapping between "Markdown conversion" and "Plain OCR") via the API.


### Environment Variables

Edit `docker-compose.yml` to adjust these settings:
- `MODEL_PATH`: Path to the model weights inside the container.
- `GPU_MEMORY_UTILIZATION`: Fraction of GPU memory to allocate (default: 0.90).

---

## 🏗️ Project Structure

```
.
├── README.md                              # This file
├── PDF_PROCESSING_WORKFLOW.md             # Detailed PDF → Image conversion explanation
├── MULTI_ARCH_BUILD.md                    # Multi-architecture build guide (AMD64 & ARM64)
├── build-multi-arch.sh                    # Script to build for both AMD64 and ARM64
├── build-arm64.sh                         # Script to build for ARM64/aarch64 only
├── build.bat                              # Windows build script
├── custom_config.py                       # Patched config (768px resolution)
├── custom_image_process_ocr2.py           # Patched vision processor
├── custom_run_dpsk_ocr_pdf.py             # PDF processing script (with image conversion)
├── start_server.py                        # FastAPI / vLLM Server
├── Dockerfile                             # Multi-platform compatible Dockerfile
├── docker-compose.yml                     # Deployment config
├── pdf_to_markdown_processor_enhanced.py  # Enhanced local processing script
└── models/                                # Directory for model weights
```

---

## 📖 Technical Documentation

### PDF Processing Details
For a comprehensive understanding of how PDFs are converted to images before OCR processing, see:
- **[PDF_PROCESSING_WORKFLOW.md](./PDF_PROCESSING_WORKFLOW.md)** - Complete technical explanation

**Key Points:**
- PDFs are rendered as images using PyMuPDF (fitz) at 144 DPI
- Each page becomes a separate PIL Image object
- Images are resized to 768x768 pixels for the model
- The DeepSeek OCR2 model is a vision transformer that requires pixel input

---

## 🤝 Support & Repo

Maintained at: [shrey2003/DeepSeek-OCR-2-Dockerized](https://github.com/shrey2003/DeepSeek-OCR-2-Dockerized)
Based on the original [DeepSeek-OCR2](https://github.com/deepseek-ai/DeepSeek-OCR2) library.
We would like to thank [Bogdanovich77/DeekSeek-OCR---Dockerized-API](https://github.com/Bogdanovich77/DeekSeek-OCR---Dockerized-API) for their previous work on DeepSeek OCR which we have further build our work on

---

## 📝 License

This project follows the same license as the DeepSeek-OCR2 project. Please refer to the official DeepSeek-OCR2 repository for licensing details.

---

## 🔄 Usage Workflow

### High-Level Flow
```mermaid
graph TD
    A[Start] --> B{Choose Method}
    
    B -->|Local Processing| C[Place PDFs in data/ folder]
    B -->|API Usage| D[Start Docker Container]
    
    C --> E[Run pdf_to_markdown_processor_enhanced.py]
    D --> F[Use API endpoints]
    
    E --> G[Check output files]
    F --> H[Process API response]
    
    G --> I[Done]
    H --> I
```

### PDF Processing Flow (Internal)
```mermaid
graph LR
    A[PDF File] -->|PyMuPDF| B[Page 1 Image]
    A -->|PyMuPDF| C[Page 2 Image]
    A -->|PyMuPDF| D[Page N Image]
    
    B -->|DeepSeek OCR2| E[Text/Markdown]
    C -->|DeepSeek OCR2| F[Text/Markdown]
    D -->|DeepSeek OCR2| G[Text/Markdown]
    
    E --> H[Combined Output]
    F --> H
    G --> H
```

**Note:** The PDF → Image conversion happens automatically. DeepSeek OCR2 cannot process PDF directly.
