# FLOPY-NET Landing Page

This is the landing page for the FLOPY-NET project - an open-source observatory for studying Federated Learning in realistic network conditions.

## Structure

```
/landing-page
├── index.html              # Main HTML file
├── /assets
│   ├── /css
│   │   └── custom.css      # Custom styles
│   ├── /js
│   │   ├── main.js         # Main JavaScript functionality
│   │   └── animations.js   # GSAP ScrollTrigger animations
│   ├── /images
│   │   └── logo.svg        # Project logo
│   └── /diagrams
│       └── components.js   # Mermaid.js diagram definitions
└── README.md               # This file
```

## Technologies Used

- **Tailwind CSS** - Utility-first CSS framework via CDN
- **Alpine.js** - Minimal JavaScript framework for interactivity
- **GSAP with ScrollTrigger** - Professional animations
- **Mermaid.js** - Diagrams from text descriptions

## Features

- Responsive design optimized for all devices
- Smooth scroll animations with GSAP
- Interactive network visualization
- Real-time animated diagrams
- Glassmorphism design effects
- Dark theme with neon accents

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
