#!/bin/bash
# Multi-Architecture Docker Build Script for DeepSeek-OCR
# Builds and pushes Docker images for both AMD64 and ARM64/aarch64 platforms

set -e

echo "🔧 Multi-Architecture Docker Build for DeepSeek-OCR"
echo "=================================================="
echo ""

# Configuration
IMAGE_NAME="${IMAGE_NAME:-shrey2003/deepseek-ocr2-dockerized}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORMS="linux/amd64,linux/arm64"

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
echo "📦 Building multi-architecture image:"
echo "   Image: $IMAGE_NAME:$IMAGE_TAG"
echo "   Platforms: $PLATFORMS"
echo ""
echo "⏳ This may take 30-60 minutes for first build (both architectures)..."
echo ""

# Ask user if they want to push
read -p "Do you want to push to Docker Hub? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    PUSH_FLAG="--push"
    echo "✅ Will push to Docker Hub after build"
else
    PUSH_FLAG="--load"
    echo "⚠️  Will only build locally (no push)"
    echo "💡 Note: --load only works for single platform builds"
    echo "   Building for current platform only..."
    PLATFORMS="linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"
fi

echo ""

# Build the image
docker buildx build \
    --platform "$PLATFORMS" \
    --tag "$IMAGE_NAME:$IMAGE_TAG" \
    $PUSH_FLAG \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build complete!"
    echo ""
    
    if [[ $PUSH_FLAG == "--push" ]]; then
        echo "🚀 Image pushed to Docker Hub:"
        echo "   $IMAGE_NAME:$IMAGE_TAG"
        echo ""
        echo "📋 To pull and use:"
        echo "   docker pull $IMAGE_NAME:$IMAGE_TAG"
        echo ""
        echo "🔍 To inspect the manifest:"
        echo "   docker buildx imagetools inspect $IMAGE_NAME:$IMAGE_TAG"
    else
        echo "💾 Image built locally"
        echo ""
        echo "🚀 To start the service:"
        echo "   docker-compose up -d"
    fi
else
    echo ""
    echo "❌ Build failed!"
    echo "💡 Possible solutions:"
    echo "   1. Ensure Docker Desktop is running"
    echo "   2. Check that you have sufficient disk space (20GB+ for multi-arch)"
    echo "   3. Try running: docker buildx prune -f"
    echo "   4. Check the error messages above"
    exit 1
fi

echo ""
