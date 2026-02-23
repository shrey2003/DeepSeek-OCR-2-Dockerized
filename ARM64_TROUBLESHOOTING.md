# ARM64 Build Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: "start_server.py": not found

**Error:**
```
ERROR: failed to solve: failed to compute cache key: "/start_server.py": not found
```

**Solution:**
The `start_server.py` file was missing from the repository. This has been fixed in the latest commit. Make sure you have the latest code:

```bash
git pull origin copilot/fix-pdf-to-image-conversion
```

### Issue 2: Base Image Platform Warning

**Warning:**
```
InvalidBaseImagePlatform: Base image vllm/vllm-openai:v0.8.5 was pulled with platform "linux/amd64", expected "linux/arm64"
```

**Explanation:**
This warning occurs because the base image `vllm/vllm-openai:v0.8.5` may not have an ARM64 variant available. Docker pulled the AMD64 version instead.

**Solutions:**

#### Option 1: Use BuildX (Recommended)
Use Docker BuildX which can cross-compile:

```bash
# Create a builder if you haven't already
docker buildx create --name multiarch-builder --use

# Build with BuildX
docker buildx build \
  --platform linux/arm64 \
  -t shrey2003/deepseek-ocr2-dockerized:arm64 \
  --load .
```

Or use the provided script:
```bash
./build-arm64.sh
```

#### Option 2: Check Base Image Availability
Check if the base image supports ARM64:

```bash
docker buildx imagetools inspect vllm/vllm-openai:v0.8.5
```

If ARM64 is not available for this version, you may need to:
1. Use a different base image version that supports ARM64
2. Use the AMD64 version (may work with emulation on Apple Silicon)
3. Build from a different base image (e.g., `nvidia/cuda:12.1.0-devel-ubuntu22.04`)

### Issue 3: Docker Daemon Not Running

**Error:**
```
ERROR: Cannot connect to the Docker daemon at unix:///Users/mac/.docker/run/docker.sock. Is the docker daemon running?
```

**Solution:**
Start Docker Desktop on macOS:
1. Open Docker Desktop application
2. Wait for it to fully start (whale icon in menu bar should be steady)
3. Try the build command again

### Issue 4: Build Context Too Large (13.57GB)

**Issue:**
```
transferring context: 13.57GB
```

**Explanation:**
The models directory is very large and takes a long time to transfer to the build context.

**Solutions:**

#### Option 1: Optimize .dockerignore
Make sure your `.dockerignore` file excludes unnecessary files:

```bash
# Create/update .dockerignore
cat > .dockerignore << 'EOF'
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so

# Documentation (exclude from build if not needed in image)
*.md
!README.md

# Build artifacts
build/
dist/
*.egg-info/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Data/outputs
data/
outputs/
*.log

# Exclude model git files if present
models/**/.git
EOF
```

#### Option 2: Use Multi-Stage Build
Consider a multi-stage Dockerfile that downloads models during build instead of copying them.

#### Option 3: Remove .git from Models
The models directory may contain a large .git folder:

```bash
# Remove .git folder from models
rm -rf models/deepseek-ai/DeepSeek-OCR2/.git
```

This can save ~6GB.

### Issue 5: ARM64 Build Takes Very Long

**Issue:**
ARM64 builds on non-ARM64 systems (like Intel Macs) use emulation and are very slow.

**Solutions:**

1. **Build on ARM64 Hardware**: If possible, build on actual ARM64 hardware (Apple Silicon Mac, ARM server)

2. **Use Pre-built Base Images**: Ensure all base images have native ARM64 support

3. **Use Docker BuildX with Multiple Builders**: Set up a remote ARM64 builder

4. **Build AMD64 and Push**: If you're on Intel Mac, build AMD64 locally and use the multi-arch script on ARM64 hardware

### Issue 6: flash-attn Installation Fails on ARM64

**Warning/Error:**
```
ERROR: Could not find a version that satisfies the requirement flash-attn==2.7.3
```

**Explanation:**
flash-attn may not be available for ARM64 architecture.

**Solution:**
The Dockerfile already handles this with `|| echo "flash-attn may already be installed"`. The build will continue without flash-attn. The model will work but may be slightly slower.

## Recommended Build Process for ARM64

### On Apple Silicon Mac (M1/M2/M3):

1. **Ensure Docker Desktop is Running**
   ```bash
   # Check Docker is running
   docker ps
   ```

2. **Update Repository**
   ```bash
   git pull origin copilot/fix-pdf-to-image-conversion
   ```

3. **Clean Models Directory** (if needed)
   ```bash
   # Remove git folder to save space and time
   rm -rf models/deepseek-ai/DeepSeek-OCR2/.git
   ```

4. **Use the Build Script**
   ```bash
   chmod +x build-arm64.sh
   ./build-arm64.sh
   ```

5. **Or Manual Build**
   ```bash
   # For local testing (no push)
   docker build --platform linux/arm64 \
     -t shrey2003/deepseek-ocr2-dockerized:arm64 .
   
   # For pushing to Docker Hub
   docker buildx build --platform linux/arm64 \
     -t shrey2003/deepseek-ocr2-dockerized:arm64 \
     --push .
   ```

### On Intel Mac or Other Non-ARM64 System:

1. **Create BuildX Builder**
   ```bash
   docker buildx create --name multiarch --use
   docker buildx inspect --bootstrap
   ```

2. **Build and Push** (cannot load locally)
   ```bash
   docker buildx build --platform linux/arm64 \
     -t shrey2003/deepseek-ocr2-dockerized:arm64 \
     --push .
   ```

## Verification

After successful build and push:

```bash
# Inspect the image
docker buildx imagetools inspect shrey2003/deepseek-ocr2-dockerized:arm64

# On ARM64 system, pull and test
docker pull shrey2003/deepseek-ocr2-dockerized:arm64
docker run --rm shrey2003/deepseek-ocr2-dockerized:arm64 uname -m
# Should output: aarch64
```

## Getting Help

If you continue to experience issues:

1. Check Docker logs: `docker logs <container-id>`
2. Verify Docker BuildX is installed: `docker buildx version`
3. Check available disk space: `df -h`
4. Review Docker Desktop settings (Resources tab)

## Summary of Fixes

The following files have been added/updated to fix the ARM64 build:
- ✅ `start_server.py` - Now included in repository (was missing)
- ✅ `.dockerignore` - Optimizes build context
- ✅ Build scripts updated with better error handling
- ✅ Documentation updated with ARM64-specific guidance
