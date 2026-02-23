# Multi-Architecture Docker Builds (AMD64 & ARM64)

This guide explains how to build and push DeepSeek-OCR2 Docker images for both AMD64 and ARM64/aarch64 architectures.

## Prerequisites

### Required Software
- **Docker** 19.03+ with BuildKit support
- **Docker Buildx** (included in Docker Desktop 19.03+)
- **Docker Hub account** (for pushing images)

### Check if Buildx is Available
```bash
docker buildx version
```

If not available, update Docker to the latest version.

## Architecture Support

### AMD64 (x86_64)
- Standard Intel/AMD processors
- Most cloud GPU instances (AWS, GCP, Azure)
- Desktop/laptop computers with Intel/AMD CPUs

### ARM64 (aarch64)
- Apple Silicon Macs (M1, M2, M3)
- AWS Graviton instances
- NVIDIA Jetson devices
- Raspberry Pi 4/5 (64-bit)
- ARM-based servers

## Build Methods

### Method 1: Build Both Architectures (Recommended)

Build and push a multi-architecture manifest that includes both AMD64 and ARM64:

```bash
chmod +x build-multi-arch.sh
./build-multi-arch.sh
```

**Options:**
- Push to Docker Hub: Select 'y' when prompted
- Build locally only: Select 'n' (builds current platform only)

**Environment Variables:**
```bash
# Customize image name and tag
IMAGE_NAME=yourusername/deepseek-ocr2 IMAGE_TAG=v1.0 ./build-multi-arch.sh
```

**What this does:**
1. Creates a Docker buildx builder with multi-platform support
2. Builds the image for both `linux/amd64` and `linux/arm64`
3. Pushes a manifest that includes both architectures
4. Users on either platform can pull the same image tag

### Method 2: Build ARM64 Only

Build only for ARM64/aarch64 architecture:

```bash
chmod +x build-arm64.sh
./build-arm64.sh
```

**Use this when:**
- You only need ARM64 support
- You want to test ARM64 build separately
- You're pushing with a specific ARM64 tag (e.g., `latest-arm64`)

### Method 3: Manual BuildX Commands

#### Build AMD64 Only
```bash
docker buildx build --platform linux/amd64 \
  -t shrey2003/deepseek-ocr2-dockerized:latest-amd64 \
  --push .
```

#### Build ARM64 Only
```bash
docker buildx build --platform linux/arm64 \
  -t shrey2003/deepseek-ocr2-dockerized:latest-arm64 \
  --push .
```

#### Build Both with Custom Manifest
```bash
# Create builder
docker buildx create --name multiarch-builder --use

# Build and push multi-arch
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t shrey2003/deepseek-ocr2-dockerized:latest \
  --push .
```

## Docker Hub Setup

### 1. Login to Docker Hub
```bash
docker login
```

Enter your Docker Hub username and password.

### 2. Tag Convention

**Recommended tags:**
- `latest` - Multi-arch manifest (AMD64 + ARM64)
- `latest-amd64` - AMD64 specific
- `latest-arm64` - ARM64 specific
- `v1.0` - Version-specific multi-arch
- `v1.0-amd64` - Version-specific AMD64
- `v1.0-arm64` - Version-specific ARM64

## Verification

### Inspect Multi-Arch Manifest
```bash
docker buildx imagetools inspect shrey2003/deepseek-ocr2-dockerized:latest
```

Expected output:
```
Name:      shrey2003/deepseek-ocr2-dockerized:latest
MediaType: application/vnd.docker.distribution.manifest.list.v2+json
Digest:    sha256:...

Manifests:
  Name:      shrey2003/deepseek-ocr2-dockerized:latest@sha256:...
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/amd64

  Name:      shrey2003/deepseek-ocr2-dockerized:latest@sha256:...
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/arm64
```

### Pull and Test on Different Platforms

**On AMD64 system:**
```bash
docker pull shrey2003/deepseek-ocr2-dockerized:latest
docker run --rm shrey2003/deepseek-ocr2-dockerized:latest uname -m
# Should output: x86_64
```

**On ARM64 system:**
```bash
docker pull shrey2003/deepseek-ocr2-dockerized:latest
docker run --rm shrey2003/deepseek-ocr2-dockerized:latest uname -m
# Should output: aarch64
```

## GitHub Actions / CI/CD

### Example GitHub Actions Workflow

Create `.github/workflows/docker-multi-arch.yml`:

```yaml
name: Build Multi-Arch Docker Image

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: shrey2003/deepseek-ocr2-dockerized

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Important Notes

### Model Weights
- Model weights are copied into the image during build
- This makes the image **very large** (~10-15GB)
- Build times will be longer for multi-arch (both architectures)
- Ensure you have sufficient disk space (30GB+ free recommended)

### Flash Attention (flash-attn)
- The `flash-attn==2.7.3` package may not be available for ARM64
- The Dockerfile uses `|| echo "..."` to continue if installation fails
- ARM64 builds may run without flash-attn (slightly slower but functional)

### GPU Support
- ARM64 builds are primarily for Apple Silicon and ARM-based edge devices
- For GPU acceleration on ARM64, you need:
  - NVIDIA Jetson: Use JetPack with CUDA support
  - Apple Silicon: Metal GPU support (different configuration)

### Build Time Estimates
- AMD64 only: 15-30 minutes
- ARM64 only: 20-40 minutes
- Both architectures: 30-60 minutes (first build)
- Subsequent builds with cache: 5-15 minutes

## Troubleshooting

### Error: "multiple platforms feature is currently not supported for docker driver"
**Solution:** Create a buildx builder with docker-container driver:
```bash
docker buildx create --name mybuilder --driver docker-container --use
```

### Error: "failed to solve: failed to copy"
**Solution:** Check that model files exist:
```bash
ls -la models/deepseek-ai/DeepSeek-OCR2/config.json
```

### Build is very slow
**Solutions:**
1. Use Docker build cache:
   ```bash
   # Don't prune between builds
   ```
2. Build one architecture at a time
3. Increase Docker's resource limits (RAM, CPU)

### ARM64 build fails with flash-attn error
**This is expected** - flash-attn may not support ARM64. The build continues without it.

### Cannot load multi-arch image locally
**Limitation:** You can only load single-platform images locally with `--load`.
For multi-arch, you must use `--push` to push to a registry.

## Best Practices

1. **Use Semantic Versioning:** Tag releases as `v1.0.0`, `v1.1.0`, etc.
2. **Keep `latest` Multi-Arch:** Always push multi-arch to `latest` tag
3. **Platform-Specific Tags:** Also push platform-specific tags for debugging
4. **Test Both Platforms:** Verify image works on both AMD64 and ARM64
5. **Document Requirements:** Update README with platform-specific requirements

## Example Complete Workflow

```bash
# 1. Download models (one-time setup)
huggingface-cli download deepseek-ai/DeepSeek-OCR2 \
  --local-dir models/deepseek-ai/DeepSeek-OCR2

# 2. Remove git folder to save space
rm -rf models/deepseek-ai/DeepSeek-OCR2/.git

# 3. Login to Docker Hub
docker login

# 4. Build and push multi-arch
./build-multi-arch.sh
# Select 'y' to push

# 5. Verify manifest
docker buildx imagetools inspect shrey2003/deepseek-ocr2-dockerized:latest

# 6. Update docker-compose.yml to use the new image
# Change: build: . 
# To: image: shrey2003/deepseek-ocr2-dockerized:latest

# 7. Test on AMD64
docker-compose up -d

# 8. Test on ARM64 (on ARM64 machine)
docker-compose up -d
```

## References

- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Multi-Platform Images](https://docs.docker.com/build/building/multi-platform/)
- [Docker Hub](https://hub.docker.com/)
