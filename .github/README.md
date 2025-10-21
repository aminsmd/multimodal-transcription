# GitHub Actions CI/CD Setup

This repository includes comprehensive GitHub Actions workflows for continuous integration, testing, and deployment.

## Workflows Overview

### 1. CI/CD Pipeline (`.github/workflows/ci.yml`)
- **Triggers**: Push to main/develop branches, pull requests, manual dispatch
- **Features**:
  - Python 3.11 testing with pytest
  - Code linting with flake8, black, and isort
  - Coverage reporting with codecov
  - Docker build and test
  - Security scanning with Trivy
  - Dependency security checks

### 2. Docker Build and Push (`.github/workflows/docker-publish.yml`)
- **Triggers**: Push to main, tags, pull requests, manual dispatch
- **Features**:
  - Multi-platform Docker builds (linux/amd64, linux/arm64)
  - Automatic tagging based on branches and semantic versioning
  - GitHub Container Registry publishing
  - Build caching for faster builds

### 3. Release Workflow (`.github/workflows/release.yml`)
- **Triggers**: Version tags (v*), manual dispatch
- **Features**:
  - Automatic release creation
  - Python package building and publishing
  - Docker image publishing for releases
  - Release notes generation

### 4. Performance Testing (`.github/workflows/performance-test.yml`)
- **Triggers**: Push to main, pull requests, manual dispatch
- **Features**:
  - Performance benchmarking
  - Memory profiling
  - Resource usage monitoring
  - PR performance comments

## Required GitHub Secrets

To enable full functionality, you need to configure the following secrets in your GitHub repository:

### Required Secrets

1. **`GOOGLE_API_KEY`**
   - **Description**: Google API key for Gemini AI transcription
   - **How to get**: 
     1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
     2. Create a new API key
     3. Copy the key
   - **Usage**: Used in CI tests and Docker builds

### Optional Secrets

2. **`CODECOV_TOKEN`** (Optional)
   - **Description**: Codecov token for enhanced coverage reporting
   - **How to get**: Sign up at [codecov.io](https://codecov.io) and get your repository token
   - **Usage**: Enhanced coverage reporting and PR comments

3. **`DOCKER_HUB_TOKEN`** (Optional)
   - **Description**: Docker Hub token for publishing to Docker Hub
   - **How to get**: 
     1. Go to Docker Hub → Account Settings → Security
     2. Create a new access token
   - **Usage**: Alternative to GitHub Container Registry

## Setting Up Secrets

1. Go to your GitHub repository
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name and value

## Workflow Features

### Automated Testing
- Runs on every push and pull request
- Tests Python code with pytest
- Validates Docker builds
- Performs security scans
- Checks code quality with linting

### Docker Integration
- Builds multi-platform Docker images
- Publishes to GitHub Container Registry
- Supports semantic versioning
- Includes build caching for performance

### Release Management
- Automatic releases on version tags
- Python package publishing
- Docker image tagging
- Release notes generation

### Performance Monitoring
- Benchmark testing
- Memory profiling
- Resource usage tracking
- Performance regression detection

## Local Development

To run the same checks locally that GitHub Actions performs:

```bash
# Install dependencies
pip install -r requirements.txt
pip install flake8 black isort pytest pytest-cov

# Run linting
black --check src/ tests/ examples/
isort --check-only src/ tests/ examples/
flake8 src/ tests/ examples/

# Run tests
pytest tests/ -v --cov=src --cov-report=html

# Build Docker image
docker build -t multimodal-transcription:test .

# Test Docker image
docker run --rm multimodal-transcription:test --help
```

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![CI/CD Pipeline](https://github.com/your-username/multimodal-transcription/workflows/CI%2FCD%20Pipeline/badge.svg)
![Docker Build](https://github.com/your-username/multimodal-transcription/workflows/Docker%20Build%20and%20Push/badge.svg)
![Release](https://github.com/your-username/multimodal-transcription/workflows/Release/badge.svg)
```

## Troubleshooting

### Common Issues

1. **Tests failing due to missing GOOGLE_API_KEY**
   - Ensure the secret is set in repository settings
   - Check that the secret name is exactly `GOOGLE_API_KEY`

2. **Docker build failures**
   - Check that Dockerfile is valid
   - Ensure all dependencies are properly specified
   - Verify build context includes all necessary files

3. **Security scan failures**
   - Review Trivy scan results
   - Update vulnerable dependencies
   - Check for security best practices

4. **Performance test failures**
   - Ensure test video is available
   - Check resource limits
   - Review memory usage patterns

### Getting Help

- Check the [Actions tab](https://github.com/your-username/multimodal-transcription/actions) for detailed logs
- Review workflow files for configuration issues
- Check repository secrets are properly configured
- Ensure all required dependencies are available

## Customization

### Adding New Workflows
1. Create a new `.yml` file in `.github/workflows/`
2. Follow the existing patterns for triggers and jobs
3. Test locally before pushing

### Modifying Existing Workflows
1. Edit the workflow files in `.github/workflows/`
2. Test changes in a feature branch first
3. Use workflow dispatch for manual testing

### Adding New Secrets
1. Add the secret to repository settings
2. Update workflow files to use the new secret
3. Document the secret in this README
