# FLOPY-NET Landing Page

This is the landing page for the FLOPY-NET project - an open-source federated learning observatory platform for studying Flower-based FL systems under realistic network conditions with comprehensive GNS3 integration and SDN control.

## Project Overview

FLOPY-NET v1.0.0-alpha.8 is a containerized research platform that combines:
- **Flower Framework**: Production-ready federated learning with PyTorch models
- **GNS3 Integration**: Realistic network topology simulation and control
- **SDN Controllers**: Ryu-based OpenFlow controllers for programmable networks
- **Policy Engine**: Centralized governance and security enforcement
- **Container Architecture**: Docker Compose with static IP assignment (192.168.100.0/24)
- **Real-time Monitoring**: React dashboard with comprehensive metrics collection

## Landing Page Structure

```
/landing-page
├── index.html              # Main HTML file with FLOPY-NET overview
├── /assets
│   ├── /css
│   │   └── custom.css      # Custom styles for FL/networking theme
│   ├── /js
│   │   ├── main.js         # Main JavaScript functionality
│   │   └── animations.js   # GSAP ScrollTrigger animations for demos
│   ├── /images
│   │   └── logo.svg        # FLOPY-NET project logo
│   └── /diagrams
│       └── components.js   # Mermaid.js federated learning architecture diagrams
└── README.md               # This file
```

## Technologies Used

- **Tailwind CSS** - Utility-first CSS framework via CDN for responsive design
- **Alpine.js** - Minimal JavaScript framework for interactive FL demo elements
- **GSAP with ScrollTrigger** - Professional animations for network topology demos
- **Mermaid.js** - Architecture diagrams showing FL server/client communication flows
- **Docker Integration** - Links to actual FLOPY-NET container documentation

## Features

- **Responsive Design**: Optimized for researchers accessing from various devices
- **Interactive FL Demos**: Animated federated learning round visualizations
- **Network Topology Visualization**: Interactive diagrams showing GNS3 integration
- **Container Architecture Overview**: Visual representation of microservices architecture
- **Real-time Metrics**: Live connection to running FLOPY-NET dashboard (if available)
- **Research Documentation**: Direct links to comprehensive technical documentation
- **Getting Started Guide**: Quick setup instructions for Docker Compose deployment

## Development

The page is built as a single HTML file with external assets. No build process required.

1. Open `index.html` in a web browser
2. All dependencies are loaded via CDN
3. Custom styles and scripts are in the `/assets` directory

## Deployment

This landing page can be deployed to:
- GitHub Pages
- Netlify
- Vercel
- Any static hosting service
- Docker container (abdulmelink/flopynet-landing-page)

### Static Deployment
Simply upload the entire `/landing-page` directory.

### Docker Deployment
The landing page can be deployed as a Docker container:

#### Using Docker directly:
```bash
# Build the Docker image
docker build -t abdulmelink/flopynet-landing-page:latest .

# Run the container
docker run -d -p 8080:80 abdulmelink/flopynet-landing-page:latest

# Push to Docker Hub
docker push abdulmelink/flopynet-landing-page:latest
```

#### Using Docker Compose:
```bash
# Build and start the container
docker-compose up -d

# Stop the container
docker-compose down

# Rebuild and restart the container
docker-compose up -d --build
```

## Performance

The page is optimized for performance:
- All libraries loaded via CDN
- Minimal custom CSS and JavaScript
- Optimized animations
- Lazy loading where appropriate

## Browser Support

Supports all modern browsers:
- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## License

Same as the main FLOPY-NET project (MIT License).
