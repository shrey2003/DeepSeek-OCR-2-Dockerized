#!/bin/bash
# Build script specifically for ARM64/aarch64 architecture
# Use this if you only want to build for ARM64

set -e

echo "🔧 ARM64/aarch64 Docker Build for DeepSeek-OCR"
echo "=============================================="
echo ""

# Configuration
IMAGE_NAME="${IMAGE_NAME:-shrey2003/deepseek-ocr2-dockerized}"
IMAGE_TAG="${IMAGE_TAG:-latest-arm64}"
PLATFORM="linux/arm64"

# Check if buildx is available
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker buildx is not available."
    echo "💡 Please install Docker with buildx support (Docker 19.03+)"
    exit 1
fi

echo "✅ Docker buildx is available"
echo ""

# Check if models directory exists
if [ ! -d "models" ]; then
    echo "⚠️  Models directory not found. Creating it..."
    mkdir -p models
    echo "💡 Please download the DeepSeek-OCR2 model to models/deepseek-ai/DeepSeek-OCR2/"
    echo "   Run: huggingface-cli download deepseek-ai/DeepSeek-OCR2 --local-dir models/deepseek-ai/DeepSeek-OCR2"
    echo ""
    exit 1
fi

# Check if model files exist
if [ ! -f "models/deepseek-ai/DeepSeek-OCR2/config.json" ]; then
    echo "❌ Model files not found in models/deepseek-ai/DeepSeek-OCR2/"
    echo "💡 Please download the model first:"
    echo "   huggingface-cli download deepseek-ai/DeepSeek-OCR2 --local-dir models/deepseek-ai/DeepSeek-OCR2"
    echo ""
    exit 1
fi

echo "✅ Model files found"
echo ""

# Create or use existing buildx builder
BUILDER_NAME="deepseek-ocr-builder"
if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "🏗️  Creating new buildx builder: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --use
else
    echo "✅ Using existing builder: $BUILDER_NAME"
    docker buildx use "$BUILDER_NAME"
fi

# Bootstrap the builder
echo "🔧 Bootstrapping builder..."
docker buildx inspect --bootstrap

echo ""
echo "📦 Building ARM64/aarch64 image:"
echo "   Image: $IMAGE_NAME:$IMAGE_TAG"
echo "   Platform: $PLATFORM"
echo ""
echo "⏳ This may take 30-60 minutes for first build..."
echo ""

# Ask user if they want to push
read -p "Do you want to push to Docker Hub? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    PUSH_FLAG="--push"
    echo "✅ Will push to Docker Hub after build"
else
    echo "❌ ARM64 builds cannot be loaded locally on non-ARM64 systems"
    echo "💡 The image will be built and cached, but you need to push to use it"
    read -p "Continue with build only (no push)? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Build cancelled."
        exit 0
    fi
    PUSH_FLAG=""
fi

echo ""

# Build the image
docker buildx build \
    --platform "$PLATFORM" \
    --tag "$IMAGE_NAME:$IMAGE_TAG" \
    $PUSH_FLAG \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ARM64 build complete!"
    echo ""
    
    if [[ $PUSH_FLAG == "--push" ]]; then
        echo "🚀 Image pushed to Docker Hub:"
        echo "   $IMAGE_NAME:$IMAGE_TAG"
        echo ""
        echo "📋 To pull and use on ARM64 system:"
        echo "   docker pull $IMAGE_NAME:$IMAGE_TAG"
        echo ""
        echo "🔍 To inspect the image:"
        echo "   docker buildx imagetools inspect $IMAGE_NAME:$IMAGE_TAG"
    else
        echo "💾 Image built and cached (not pushed)"
        echo "💡 To push later, run with push flag or use multi-arch script"
    fi
else
    echo ""
    echo "❌ Build failed!"
    echo "💡 Possible solutions:"
    echo "   1. Ensure Docker Desktop is running"
    echo "   2. Check that you have sufficient disk space (15GB+)"
    echo "   3. Try running: docker buildx prune -f"
    echo "   4. Check the error messages above"
    exit 1
fi

echo ""
