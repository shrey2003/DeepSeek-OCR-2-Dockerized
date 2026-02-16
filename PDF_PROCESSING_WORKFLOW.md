# PDF Processing Workflow in DeepSeek-OCR-2-Dockerized

## Question: Does DeepSeek OCR Accept PDF Directly?

**Short Answer: NO** - The DeepSeek OCR model does NOT accept PDF files as direct input. PDFs are **always converted to images first** before being processed by the OCR model.

## Why PDFs Are Converted to Images

The DeepSeek OCR2 model is a **vision-language model** that processes image data, not PDF documents directly. Like other vision models (GPT-4V, LLaVA, etc.), it requires image input with pixel data. PDFs are structured document formats that need to be rendered as images before the model can "see" and process their visual content.

## Technical Implementation

### 1. Local Processing (custom_run_dpsk_ocr_pdf.py)

When processing PDFs locally using the `custom_run_dpsk_ocr_pdf.py` script, the workflow is:

```
PDF File → PyMuPDF (fitz) → Individual Page Images → DeepSeek OCR2 Model → Text/Markdown Output
```

#### Code Implementation Details

**Step 1: PDF to Images Conversion**
```python
def pdf_to_images_high_quality(pdf_path, dpi=144, image_format="PNG"):
    """
    Converts PDF pages to high-quality images using PyMuPDF (fitz)
    
    Parameters:
    - pdf_path: Path to the PDF file
    - dpi: Resolution (default 144 DPI for good quality)
    - image_format: Output format (PNG/JPG)
    
    Returns: List of PIL Image objects (one per page)
    """
    images = []
    pdf_document = fitz.open(pdf_path)  # Open PDF with PyMuPDF
    
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        # Render page to pixmap at specified resolution
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        
        # Convert pixmap to PIL Image
        img_data = pixmap.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        images.append(img)
    
    pdf_document.close()
    return images
```

**Step 2: Image Processing and OCR**
```python
# Each image is processed individually
for image in images:
    # The image is tokenized and prepared for the model
    cache_item = {
        "prompt": prompt,
        "multi_modal_data": {
            "image": DeepseekOCRProcessor().tokenize_with_images(
                images=[image], 
                bos=True, 
                eos=True, 
                cropping=CROP_MODE
            )
        },
    }
    
    # Then fed to the vLLM engine
    outputs = llm.generate([cache_item], sampling_params=sampling_params)
```

### 2. API Processing (pdf_to_markdown_processor.py)

When processing PDFs through the API endpoint (`/ocr/pdf`), the same conversion happens:

```
PDF File Upload → FastAPI Server → PyMuPDF Conversion → Page Images → DeepSeek OCR2 → JSON Response
```

#### API Workflow

1. **Client uploads PDF** via multipart/form-data:
   ```bash
   curl -X POST "http://localhost:8000/ocr/pdf" \
     -F "file=@document.pdf" \
     -F "prompt=<image>\nConvert to markdown."
   ```

2. **Server receives PDF** and converts each page to an image

3. **Each page image** is processed by the DeepSeek OCR2 model

4. **Results are aggregated** and returned as a batch response:
   ```json
   {
     "results": [
       {"result": "Page 1 content...", "page_count": 1},
       {"result": "Page 2 content...", "page_count": 2}
     ],
     "total_pages": 2,
     "filename": "document.pdf"
   }
   ```

### 3. Enhanced Processors

The enhanced processors (`pdf_to_markdown_processor_enhanced.py`, `pdf_to_ocr_enhanced.py`) follow the same pattern but add post-processing:

```
PDF → Images → OCR Processing → Layout Analysis → Image Extraction → Cleaned Markdown
```

Features include:
- **Layout detection**: Identifies tables, images, titles from special tokens
- **Image extraction**: Extracts embedded images using coordinates
- **Reference cleanup**: Removes layout reference tags from final output
- **Format optimization**: Cleans up markdown formatting

## Key Components

### PyMuPDF (fitz)
- Library used for PDF rendering
- Converts each PDF page to a pixmap (raster image)
- Configurable resolution (DPI) for quality control

### Resolution Settings
- **Default DPI**: 144 DPI (good balance of quality and size)
- **Calculation**: `zoom = dpi / 72.0`
- Higher DPI = Better quality but larger images and more processing time

### Image Format
- **Internal format**: PNG (lossless)
- **Model input**: Processed to 768x768 pixel tensors
- DeepSeek-OCR2 is optimized for 768x768 resolution

## Why This Approach?

1. **Model Architecture**: DeepSeek OCR2 is a vision transformer that requires pixel inputs
2. **Flexibility**: Images can be preprocessed, enhanced, or cropped before OCR
3. **Consistency**: Same model handles both standalone images and PDF-derived images
4. **Layout Preservation**: Rendering preserves visual layout, fonts, and formatting

## Performance Considerations

### Memory Usage
- Each PDF page becomes an image in memory
- Large PDFs with many pages require more RAM
- Images are processed sequentially or in batches

### Processing Time
| Step | Typical Time |
|------|--------------|
| PDF → Image (1 page) | ~100-200ms |
| OCR Processing (1 page) | ~2-5 seconds |
| Post-processing | ~50-100ms |

### Optimization Tips
1. **Batch Processing**: Process multiple pages in parallel with `MAX_CONCURRENCY`
2. **Resolution**: Use lower DPI for faster processing if high quality isn't critical
3. **Cropping**: Enable `CROP_MODE` to process only relevant regions

## Summary

**The DeepSeek OCR model does NOT accept PDF files directly.** All PDFs are converted to images first using PyMuPDF (fitz), then each page image is processed by the vision-language model. This is a fundamental requirement of how vision-based OCR models work - they need pixel data, not document structure.

This workflow is implemented consistently across:
- Local processing scripts (`custom_run_dpsk_ocr_pdf.py`)
- API endpoints (`/ocr/pdf`)
- Enhanced processors (`pdf_to_markdown_processor_enhanced.py`)

The conversion is automatic and transparent to the end user, but it's important to understand that:
1. PDF processing is inherently slower than image processing (due to conversion overhead)
2. Memory usage scales with the number of pages
3. The quality of OCR depends on the rendering resolution (DPI setting)
