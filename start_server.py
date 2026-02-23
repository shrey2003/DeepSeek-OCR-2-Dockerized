#!/usr/bin/env python3
"""
FastAPI Server for DeepSeek-OCR2
Provides REST API endpoints for OCR processing on images and PDFs
"""

import os
import sys
import io
import base64
import logging
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

import torch
import fitz  # PyMuPDF
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Setup paths
sys.path.insert(0, '/app/DeepSeek-OCR2-vllm')

# Import DeepSeek OCR components
from config import MODEL_PATH, PROMPT, CROP_MODE
from deepseek_ocr2 import DeepseekOCR2ForCausalLM
from vllm.model_executor.models.registry import ModelRegistry
from vllm import LLM, SamplingParams
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor
from process.image_process import DeepseekOCR2Processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
llm = None
sampling_params = None
processor = None

# Environment configuration
if torch.version.cuda == '11.8':
    os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda-11.8/bin/ptxas"
os.environ['VLLM_USE_V1'] = '0'
os.environ["CUDA_VISIBLE_DEVICES"] = os.getenv("CUDA_VISIBLE_DEVICES", "0")

# Get configuration from environment
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "5"))
GPU_MEMORY_UTILIZATION = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.85"))

# Response models
class OCRResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    page_count: int = 1

class PageResult(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    page_number: int

class BatchOCRResponse(BaseModel):
    success: bool
    results: List[PageResult]
    total_pages: int
    filename: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_path: str
    cuda_available: bool
    cuda_device_count: int

def initialize_model():
    """Initialize the DeepSeek OCR2 model and processor"""
    global llm, sampling_params, processor
    
    logger.info("Initializing DeepSeek OCR2 model...")
    logger.info(f"Model path: {MODEL_PATH}")
    logger.info(f"Max concurrency: {MAX_CONCURRENCY}")
    logger.info(f"GPU memory utilization: {GPU_MEMORY_UTILIZATION}")
    
    # Register the model
    ModelRegistry.register_model("DeepseekOCR2ForCausalLM", DeepseekOCR2ForCausalLM)
    
    # Initialize vLLM
    llm = LLM(
        model=MODEL_PATH,
        hf_overrides={"architectures": ["DeepseekOCR2ForCausalLM"]},
        block_size=256,
        enforce_eager=False,
        trust_remote_code=True,
        max_model_len=8192,
        swap_space=0,
        max_num_seqs=MAX_CONCURRENCY,
        tensor_parallel_size=1,
        gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
        disable_mm_preprocessor_cache=True
    )
    
    # Setup logits processors
    logits_processors = [
        NoRepeatNGramLogitsProcessor(
            ngram_size=20, 
            window_size=50, 
            whitelist_token_ids={128821, 128822}
        )
    ]
    
    # Setup sampling parameters
    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=8192,
        logits_processors=logits_processors,
        skip_special_tokens=False,
        include_stop_str_in_output=True,
    )
    
    # Initialize processor
    processor = DeepseekOCR2Processor()
    
    logger.info("Model initialized successfully!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    initialize_model()
    yield
    # Shutdown
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="DeepSeek-OCR2 API",
    description="OCR API for processing images and PDFs using DeepSeek-OCR2",
    version="1.0.0",
    lifespan=lifespan
)

def pdf_to_images(pdf_bytes: bytes, dpi: int = 144) -> List[Image.Image]:
    """
    Convert PDF bytes to list of PIL Images.
    
    Note: DeepSeek OCR2 does NOT accept PDF directly - PDFs must be converted
    to images first as the model is a vision transformer that requires pixel input.
    """
    images = []
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        
        Image.MAX_IMAGE_PIXELS = None
        img_data = pixmap.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        images.append(img)
    
    pdf_document.close()
    return images

def process_image_with_prompt(image: Image.Image, prompt: str) -> str:
    """Process a single image with the OCR model"""
    cache_item = {
        "prompt": prompt,
        "multi_modal_data": {
            "image": processor.tokenize_with_images(
                images=[image], 
                bos=True, 
                eos=True, 
                cropping=CROP_MODE
            )
        },
    }
    
    outputs = llm.generate([cache_item], sampling_params=sampling_params)
    result = outputs[0].outputs[0].text
    
    # Clean up the result
    if '<｜end▁of▁sentence｜>' in result:
        result = result.replace('<｜end▁of▁sentence｜>', '')
    
    return result

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if llm is not None else "initializing",
        model_loaded=llm is not None,
        model_path=MODEL_PATH,
        cuda_available=torch.cuda.is_available(),
        cuda_device_count=torch.cuda.device_count() if torch.cuda.is_available() else 0
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DeepSeek-OCR2 API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "ocr_image": "/ocr/image",
            "ocr_pdf": "/ocr/pdf"
        }
    }

@app.post("/ocr/image", response_model=OCRResponse)
async def ocr_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """
    Process a single image file with OCR
    
    Args:
        file: Image file (JPG, PNG, etc.)
        prompt: Custom prompt (optional, defaults to config PROMPT)
    """
    try:
        if llm is None:
            raise HTTPException(status_code=503, detail="Model not initialized")
        
        # Read image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Use provided prompt or default
        ocr_prompt = prompt if prompt else PROMPT
        
        # Process image
        result = process_image_with_prompt(image, ocr_prompt)
        
        return OCRResponse(
            success=True,
            result=result,
            page_count=1
        )
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        return OCRResponse(
            success=False,
            error=str(e),
            page_count=0
        )

@app.post("/ocr/pdf", response_model=BatchOCRResponse)
async def ocr_pdf(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """
    Process a PDF file with OCR
    
    Note: PDFs are converted to images first (one per page) before OCR processing.
    DeepSeek OCR2 is a vision model that requires image input, not PDF structure.
    
    Args:
        file: PDF file
        prompt: Custom prompt (optional, defaults to config PROMPT)
    """
    try:
        if llm is None:
            raise HTTPException(status_code=503, detail="Model not initialized")
        
        # Read PDF
        pdf_bytes = await file.read()
        
        # Convert PDF to images (REQUIRED - model doesn't accept PDF directly)
        logger.info(f"Converting PDF '{file.filename}' to images...")
        images = pdf_to_images(pdf_bytes)
        logger.info(f"Converted {len(images)} pages to images")
        
        # Use provided prompt or default
        ocr_prompt = prompt if prompt else PROMPT
        
        # Process each page
        results = []
        for idx, image in enumerate(images):
            try:
                result_text = process_image_with_prompt(image, ocr_prompt)
                results.append(PageResult(
                    success=True,
                    result=result_text,
                    page_number=idx + 1
                ))
            except Exception as e:
                logger.error(f"Error processing page {idx + 1}: {str(e)}")
                results.append(PageResult(
                    success=False,
                    error=str(e),
                    page_number=idx + 1
                ))
        
        return BatchOCRResponse(
            success=True,
            results=results,
            total_pages=len(images),
            filename=file.filename
        )
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting DeepSeek-OCR2 API server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
