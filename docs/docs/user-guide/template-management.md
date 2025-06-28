# GNS3 Template Management

This guide covers the comprehensive management of GNS3 templates for FLOPY-NET, including registration, custom image deployment, and template lifecycle management using the `scripts/gns3_templates.py` script.

## Overview

The FLOPY-NET template management system provides automated tools for deploying and managing Docker-based GNS3 templates. The system supports both base FLOPY-NET images and custom images built on top of the FLOPY-NET foundation.

## Template Registration Script

The `scripts/gns3_templates.py` script is the primary tool for managing GNS3 templates. It provides a comprehensive command-line interface for template lifecycle management.

### Script Capabilities

The `gns3_templates.py` script provides comprehensive template management functionality for FLOPY-NET deployments. The script's template registration capability allows you to automatically register new templates from JSON definitions stored in the configuration directory, streamlining the deployment process and ensuring consistency across different GNS3 environments.

Template listing functionality enables you to view all existing templates with sophisticated filtering options, helping you understand what components are currently available in your GNS3 server and identify any missing or outdated templates. The cleaning feature provides pattern-based template removal, allowing you to maintain a clean template repository by removing obsolete or conflicting template definitions.

Image update capabilities ensure that your templates always reference the latest Docker image versions, automatically updating template definitions when new versions of FLOPY-NET components become available. The script also provides robust support for custom templates, enabling organizations to deploy their own images built on top of the FLOPY-NET foundation while maintaining compatibility with the core system architecture.

### Basic Usage

```powershell
# Show all available commands
python scripts\gns3_templates.py --help

# Register all FLOPY-NET templates
python scripts\gns3_templates.py register --host 192.168.56.100

# List registered templates
python scripts\gns3_templates.py list --host 192.168.56.100

# Clean templates matching a pattern
python scripts\gns3_templates.py clean --host 192.168.56.100 --pattern flopynet

# Update template images
python scripts\gns3_templates.py update --host 192.168.56.100
```

## Template Registration Workflow

### 1. Base Template Registration

The standard workflow for registering FLOPY-NET base templates:

```powershell
# Step 1: Ensure GNS3 VM is running and accessible
ping 192.168.56.100

# Step 2: Verify GNS3 API is accessible
curl http://192.168.56.100:3080/v2/version

# Step 3: Register templates
cd d:\dev\microfed\codebase
python scripts\gns3_templates.py register --host 192.168.56.100 --port 3080 --verbose

# Step 4: Verify registration
python scripts\gns3_templates.py list --host 192.168.56.100 --flopynet-only
```

### 2. Template Directory Structure

Templates are defined in JSON files located in `config/gns3/templates/`:

```
config/gns3/templates/
├── fl_server.json          # FL Server template
├── fl_client.json          # FL Client template
├── policy_engine.json      # Policy Engine template
├── collector.json          # Collector template
├── sdn_controller.json     # SDN Controller template
└── openvswitch.json        # OpenVSwitch template
```

### 3. Template Definition Format

Each template is defined as a JSON file with the following structure:

```json
{
  "name": "flopynet-FLServer",
  "template_type": "docker",
  "image": "abdulmelink/flopynet-server:latest",
  "adapters": 1,
  "console_type": "telnet",
  "category": "guest",
  "symbol": ":/symbols/docker_guest.svg",
  "environment": {
    "SERVICE_TYPE": "fl-server",
    "FL_SERVER_PORT": "8080",
    "FL_METRICS_PORT": "8081",
    "POLICY_ENGINE_URL": "http://192.168.141.20:5000"
  }
}
```

## Custom Image Management

Custom images in FLOPY-NET provide researchers and organizations the flexibility to extend the base platform functionality while maintaining compatibility with the core system architecture. These custom implementations enable specialized federated learning scenarios, advanced model architectures, and domain-specific optimizations that build upon the proven FLOPY-NET foundation.

When building custom images, the recommended approach involves extending the existing FLOPY-NET base images rather than creating completely new containers from scratch. This approach ensures that all core functionality, metric collection interfaces, and system integration points remain intact while allowing you to add your specific enhancements and customizations.

### 1. Building Custom Images

The process of building custom images requires careful attention to maintaining compatibility with the FLOPY-NET ecosystem while adding your desired functionality. Custom images should extend FLOPY-NET base images and preserve all critical system interfaces, particularly the metric collection endpoints that enable the Collector service to monitor system performance and federated learning progress.

Here's an example of creating a custom FL client with additional machine learning libraries and specialized model implementations:

```dockerfile
# Example: Custom FL Client with additional ML libraries
FROM abdulmelink/flopynet-client:latest

# Add custom dependencies
RUN pip install transformers torch-audio scikit-image

# Add custom model implementations
COPY custom_models/ /app/custom_models/
COPY custom_config.json /app/config/

# Set custom environment variables
ENV CUSTOM_MODEL_PATH=/app/custom_models
ENV ENABLE_CUSTOM_FEATURES=true

WORKDIR /app
ENTRYPOINT ["/app/entrypoint-fl-client.sh"]
```

### 2. Custom Template Creation

Creating effective template definitions for custom images requires understanding both the GNS3 template format and the specific requirements of your custom implementation. The template definition serves as the bridge between your custom Docker image and the GNS3 environment, specifying how the container should be configured, what network interfaces it needs, and what environment variables are required for proper operation.

When designing custom templates, it's essential to maintain compatibility with the FLOPY-NET service discovery and communication patterns. This includes preserving the standard environment variables that enable components to locate and communicate with each other, while adding your custom configuration parameters that enable the enhanced functionality provided by your custom image.

The following example demonstrates a template definition for a custom FL client specialized for natural language processing tasks:

```json
{
  "name": "Custom-FLClient-NLP",
  "template_type": "docker",
  "image": "your-org/custom-flopynet-client-nlp:v1.0",
  "adapters": 1,
  "console_type": "telnet",
  "category": "guest",
  "symbol": ":/symbols/docker_guest.svg",
  "environment": {
    "SERVICE_TYPE": "fl-client",
    "CLIENT_TYPE": "nlp_specialized",
    "CUSTOM_MODEL_PATH": "/app/custom_models",
    "ENABLE_CUSTOM_FEATURES": "true",
    "FL_SERVER_HOST": "192.168.141.10",
    "FL_SERVER_PORT": "8080",
    "POLICY_ENGINE_URL": "http://192.168.141.20:5000"
  }
}
```

### 3. Custom Template Registration

The registration process for custom templates follows the same systematic approach as base templates but requires additional consideration for custom image deployment and registry management. Before registering custom templates, ensure that the corresponding Docker images are available in the GNS3 VM environment, either through direct image loading or registry-based deployment.

The registration workflow involves creating a dedicated directory for custom templates to maintain separation from base system templates, copying your custom template definitions to this directory, and using the registration script with appropriate parameters to deploy the templates to your GNS3 server.

Once registered, custom templates become available in the GNS3 interface alongside standard FLOPY-NET templates, enabling researchers to build complex network topologies that combine base components with specialized custom implementations. The verification step ensures that templates are properly registered and accessible for scenario deployment.

```powershell
# Create custom templates directory
mkdir config\gns3\custom-templates

# Copy custom template definition
copy custom_fl_client_nlp.json config\gns3\custom-templates\

# Register custom templates
python scripts\gns3_templates.py register --host 192.168.56.100 --templates-dir config\gns3\custom-templates

# Verify custom template registration
python scripts\gns3_templates.py list --host 192.168.56.100 | findstr Custom
```

## Advanced Template Management

Advanced template management encompasses sophisticated workflows for maintaining multiple template versions, performing bulk operations across template collections, and ensuring template quality through validation processes. These capabilities become increasingly important as research environments grow in complexity and require more sophisticated deployment strategies.

Template versioning enables research reproducibility by allowing you to maintain multiple versions of templates corresponding to different experimental configurations or software releases. This capability is essential for longitudinal studies where you need to replicate earlier experimental conditions or compare results across different platform versions.

### 1. Template Versioning

Template versioning provides crucial capability for research environments where experimental reproducibility and systematic comparison of different platform versions are essential requirements. The versioning system enables you to maintain multiple concurrent versions of templates, each corresponding to specific experimental configurations, software releases, or research phases.

When managing template versions, the registration process can target specific version tags, ensuring that your GNS3 environment uses precisely the Docker image versions required for your research scenario. The update mechanism allows you to migrate existing templates to newer versions while preserving the ability to roll back to previous versions if issues are discovered.

Version information becomes particularly valuable when conducting comparative studies or reproducing earlier experimental results, as it provides a clear audit trail of exactly which software versions were used in each experimental configuration.

```powershell
# Register templates with specific version tags
python scripts\gns3_templates.py register --host 192.168.56.100 --registry abdulmelink --tag v1.0.1

# Update existing templates to new versions
python scripts\gns3_templates.py update --host 192.168.56.100 --tag v1.0.2

# List templates with version information
python scripts\gns3_templates.py list --host 192.168.56.100 --verbose
```

### 2. Bulk Template Operations

Bulk template operations provide essential efficiency gains when managing large numbers of templates or performing systematic maintenance across your entire GNS3 environment. These operations become particularly valuable during platform upgrades, when migrating between different experimental phases, or when cleaning up obsolete experimental configurations.

The bulk cleaning capability allows you to remove entire families of templates based on pattern matching, which is especially useful when transitioning between major platform versions or removing experimental templates that are no longer needed. This systematic approach prevents template repository clutter and reduces the likelihood of accidentally using outdated configurations.

Bulk registration enables rapid deployment of complete template sets, which is invaluable when setting up new research environments or replicating experimental configurations across multiple GNS3 servers. The bulk update functionality ensures that all templates in your environment can be migrated to new software versions simultaneously, maintaining consistency across your entire experimental infrastructure.

```powershell
# Clean all FLOPY-NET templates
python scripts\gns3_templates.py clean --host 192.168.56.100 --pattern flopynet

# Re-register all templates
python scripts\gns3_templates.py register --host 192.168.56.100

# Update all template images to latest versions
python scripts\gns3_templates.py update --host 192.168.56.100
```

### 3. Template Validation

Template validation represents a critical quality assurance step in the template management lifecycle, ensuring that template definitions are syntactically correct, semantically meaningful, and compatible with the target GNS3 environment before deployment. This validation process prevents deployment failures and reduces troubleshooting time by catching configuration errors early in the development process.

The validation process examines template JSON syntax, verifies that required fields are present and correctly formatted, and checks that referenced Docker images exist and are accessible. Advanced validation capabilities can also verify that environment variable configurations are consistent with the expected service interfaces and that network adapter configurations are appropriate for the intended deployment scenarios.

Dry-run functionality provides an additional layer of safety by simulating the registration process without actually modifying the GNS3 server state. This capability allows you to verify that templates will register successfully and identify any potential conflicts or issues before committing to the actual deployment. Post-registration testing functionality ensures that registered templates are not only syntactically correct but also functionally operational within the GNS3 environment.

```powershell
# Validate template definitions before registration
python scripts\gns3_templates.py validate --templates-dir config\gns3\templates

# Test template registration without actual deployment
python scripts\gns3_templates.py register --host 192.168.56.100 --dry-run

# Verify template functionality after registration
python scripts\gns3_templates.py test --host 192.168.56.100 --template flopynet-FLServer
```

## Image Deployment Workflow

The image deployment workflow represents a fundamental aspect of FLOPY-NET template management, encompassing the systematic process of making Docker images available within the GNS3 VM environment. This workflow ensures that all necessary container images are properly staged and accessible before template registration and scenario execution.

Understanding the deployment workflow is essential for researchers who need to manage both base FLOPY-NET images and custom images built for specific research requirements. The deployment process varies depending on whether you're working with standard images from the public registry or custom images that require special handling for transfer and registration.

### 1. Base Image Deployment

Base image deployment involves systematically pulling and verifying the core FLOPY-NET Docker images within the GNS3 VM environment. This process establishes the foundation for all FLOPY-NET scenarios and ensures that the essential components are available for template registration and scenario execution.

The deployment process begins with establishing SSH connectivity to the GNS3 VM and verifying that the Docker daemon is operational and properly configured. Once connectivity is confirmed, the deployment proceeds with pulling each required image from the registry, maintaining careful attention to version consistency across all components.

Image verification after deployment ensures that all required images are properly downloaded, correctly tagged, and ready for use in template registration. This verification step prevents runtime failures that could occur if images are missing or corrupted during the deployment process.

```bash
# SSH into GNS3 VM
ssh gns3@192.168.56.100

# Pull FLOPY-NET base images
docker pull abdulmelink/flopynet-server:latest
docker pull abdulmelink/flopynet-client:latest
docker pull abdulmelink/flopynet-policy-engine:latest
docker pull abdulmelink/flopynet-collector:latest
docker pull abdulmelink/flopynet-sdn-controller:latest
docker pull abdulmelink/flopynet-openvswitch:latest

# Verify images
docker images | grep abdulmelink
```

### 2. Custom Image Deployment

```powershell
# Build custom image on host
docker build -f Dockerfile.custom-client -t your-org/custom-flopynet-client:v1.0 .

# Save and transfer image
docker save your-org/custom-flopynet-client:v1.0 | gzip > custom-client.tar.gz
scp custom-client.tar.gz gns3@192.168.56.100:/tmp/

# Load image in GNS3 VM
ssh gns3@192.168.56.100
docker load < /tmp/custom-client.tar.gz
docker images | grep custom-flopynet-client
```

### 3. Registry-based Deployment

```bash
# Alternative: Use Docker registry for custom images
# Push to registry from host
docker tag your-org/custom-flopynet-client:v1.0 your-registry.com/custom-flopynet-client:v1.0
docker push your-registry.com/custom-flopynet-client:v1.0

# Pull from registry in GNS3 VM
ssh gns3@192.168.56.100
docker pull your-registry.com/custom-flopynet-client:v1.0
```

## Troubleshooting

### Common Issues

#### Template Registration Failures

```powershell
# Check GNS3 server connectivity
curl http://192.168.56.100:3080/v2/version

# Verify template JSON syntax
python -m json.tool config\gns3\templates\fl_server.json

# Register with verbose output for debugging
python scripts\gns3_templates.py register --host 192.168.56.100 --verbose
```

#### Image Not Found Errors

```bash
# Verify image exists in GNS3 VM
ssh gns3@192.168.56.100
docker images | grep flopynet

# Check image naming and tags
docker inspect abdulmelink/flopynet-server:latest
```

#### Template Conflicts

```powershell
# Clean conflicting templates
python scripts\gns3_templates.py clean --host 192.168.56.100 --pattern conflicting-name

# Re-register with correct configuration
python scripts\gns3_templates.py register --host 192.168.56.100
```

### Diagnostic Commands

```powershell
# Get detailed template information
curl http://192.168.56.100:3080/v2/templates | ConvertFrom-Json | Format-Table

# Check template API response
curl -X GET "http://192.168.56.100:3080/v2/templates" -H "accept: application/json"

# Validate GNS3 server configuration
python scripts\check_gns3_connectivity.py --host 192.168.56.100
```

## Best Practices

### 1. Template Naming Conventions

- Use consistent naming: `organization-ComponentType`
- Include version information in image tags
- Use descriptive template names that indicate functionality

### 2. Environment Variables

- Use uppercase for environment variable names
- Group related variables by functionality
- Include default values in template definitions

### 3. Image Management

- Keep custom images lightweight by extending base images
- Use multi-stage builds for complex custom images
- Tag images with semantic versions

### 4. Template Lifecycle

1. **Development**: Create and test templates locally
2. **Validation**: Validate template definitions before deployment
3. **Registration**: Register templates in GNS3
4. **Testing**: Test template functionality in GNS3 projects
5. **Production**: Deploy to production GNS3 environments
6. **Maintenance**: Update templates and images as needed

This comprehensive template management system ensures reliable and scalable deployment of FLOPY-NET components in GNS3 environments.
