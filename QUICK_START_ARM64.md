# Quick Start: Building and Pushing ARM64 Images

This is a quick reference for building and pushing DeepSeek-OCR2 Docker images for ARM64/aarch64 architecture.

## TL;DR - Just Build and Push ARM64

```bash
# Make script executable
chmod +x build-arm64.sh

# Run the build script
./build-arm64.sh

# When prompted "Do you want to push to Docker Hub? (y/n):"
# Press 'y' to push the image
```

## TL;DR - Build Both AMD64 and ARM64

```bash
# Make script executable
chmod +x build-multi-arch.sh

# Run the build script
./build-multi-arch.sh

# When prompted "Do you want to push to Docker Hub? (y/n):"
# Press 'y' to push both architectures
```

## What You Need

1. **Docker login** (required for pushing):
   ```bash
   docker login
   ```

2. **Model weights downloaded** at `models/deepseek-ai/DeepSeek-OCR2/`

3. **Sufficient disk space**: 30GB+ free for multi-arch builds

## Customizing Image Name

```bash
# Change the image name and tag
IMAGE_NAME=yourusername/your-image-name IMAGE_TAG=v1.0 ./build-multi-arch.sh
```

## After Building

### Verify the Multi-Arch Manifest
```bash
docker buildx imagetools inspect shrey2003/deepseek-ocr2-dockerized:latest
```

You should see both platforms listed:
- `Platform: linux/amd64`
- `Platform: linux/arm64`

### Update docker-compose.yml
Change from building locally to using the pushed image:

```yaml
services:
  deepseek-ocr:
    image: shrey2003/deepseek-ocr2-dockerized:latest  # Use pre-built image
    # build: .  # Comment out or remove this line
    ...
```

### Test on Different Platforms

**On any AMD64 machine:**
```bash
docker pull shrey2003/deepseek-ocr2-dockerized:latest
docker run --rm shrey2003/deepseek-ocr2-dockerized:latest uname -m
# Output: x86_64
```

**On any ARM64 machine (Apple Silicon, ARM servers, etc.):**
```bash
docker pull shrey2003/deepseek-ocr2-dockerized:latest
docker run --rm shrey2003/deepseek-ocr2-dockerized:latest uname -m
# Output: aarch64
```

## Common Issues

### "buildx: command not found"
**Solution:** Update Docker to version 19.03 or later.

### "multiple platforms feature is currently not supported"
**Solution:** The script automatically creates a buildx builder. If it fails, manually create one:
```bash
docker buildx create --name mybuilder --driver docker-container --use
```

### "Cannot load multi-arch image locally"
**This is expected.** Multi-arch images must be pushed to a registry. Select 'y' when prompted to push.

### Build is slow
**Normal.** Multi-arch builds take 30-60 minutes initially. Subsequent builds are faster due to caching.

## For More Details

See [MULTI_ARCH_BUILD.md](./MULTI_ARCH_BUILD.md) for comprehensive documentation.
