# Build script for RunPod Docker image
# Usage: .\build.ps1

Write-Host "Building Vexa Transcription Service for RunPod..." -ForegroundColor Cyan

# Check if Docker is running
docker version > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build the image
Write-Host "`nBuilding Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.runpod -t vexa-transcription:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Build successful!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Tag your image: docker tag vexa-transcription:latest YOUR_USERNAME/vexa-transcription:latest"
    Write-Host "2. Login to Docker Hub: docker login"
    Write-Host "3. Push to Docker Hub: docker push YOUR_USERNAME/vexa-transcription:latest"
} else {
    Write-Host "`n❌ Build failed. Check the errors above." -ForegroundColor Red
    exit 1
}
