/**
 * Copyright (c) 2025 Abdulmelik Saylan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Main JavaScript for FLOPY-NET landing page
// Enhanced with performance optimizations and fixed diagram positioning

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeNetworkAnimation();
    initializeMermaidDiagrams();
    initializeSmoothScrolling();
    
    // Add intersection observer for animations
    if ('IntersectionObserver' in window) {
        observeElements();
    }
});

// Network animation background
function initializeNetworkAnimation() {
    const canvas = document.createElement('canvas');
    const networkContainer = document.getElementById('network-animation');
    
    if (!networkContainer) return;
    
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';
    canvas.style.opacity = '0.3';
    
    networkContainer.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    let animationId;
    let particles = [];
    
    function resizeCanvas() {
        canvas.width = networkContainer.offsetWidth;
        canvas.height = networkContainer.offsetHeight;
        
        // Recreate particles for new canvas size
        particles = createParticles();
    }
    
    function createParticles() {
        const particles = [];
        const particleCount = Math.min(50, Math.floor(canvas.width / 20));
        
        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.8,
                vy: (Math.random() - 0.5) * 0.8,
                size: Math.random() * 2 + 1
            });
        }
        return particles;
    }
    
    // Initialize particles
    particles = createParticles();
    
    function drawConnections() {
        ctx.strokeStyle = 'rgba(121, 192, 255, 0.2)';
        ctx.lineWidth = 1;
        
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 100) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.globalAlpha = 1 - distance / 100;
                    ctx.stroke();
                    ctx.globalAlpha = 1;
                }
            }
        }
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw connections between particles
        drawConnections();
        
        // Update and draw particles
        particles.forEach(particle => {
            // Update position
            particle.x += particle.vx;
            particle.y += particle.vy;
            
            // Bounce off walls
            if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
            if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
            
            // Keep particles in bounds
            particle.x = Math.max(0, Math.min(canvas.width, particle.x));
            particle.y = Math.max(0, Math.min(canvas.height, particle.y));
              // Draw particle with enhanced visibility
            ctx.fillStyle = 'rgba(121, 192, 255, 0.9)'; // Increased opacity from 0.8 to 0.9
            ctx.shadowColor = 'rgba(121, 192, 255, 0.6)';
            ctx.shadowBlur = 8;
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size * 1.5, 0, Math.PI * 2); // Increased size by 1.5x
            ctx.fill();
            ctx.shadowBlur = 0; // Reset shadow
        });
        
        animationId = requestAnimationFrame(animate);
    }
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    animate();
}

// Initialize Mermaid diagrams with enhanced configuration
function initializeMermaidDiagrams() {
    // Wait for mermaid to be available
    if (typeof mermaid === 'undefined') {
        setTimeout(initializeMermaidDiagrams, 100);
        return;
    }    // Configure Mermaid with TEXT-FIRST approach to prevent cutoff
    mermaid.initialize({
        theme: 'base',
        themeVariables: {
            primaryColor: '#79c0ff',
            primaryTextColor: '#f0f6fc',
            primaryBorderColor: '#58a6ff',
            lineColor: '#79c0ff',
            secondaryColor: '#21262d',
            tertiaryColor: '#161b22',
            background: '#0d1117',
            darkMode: true,
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '18px'
        },
        startOnLoad: false,
        securityLevel: 'loose',
        flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis',
            // TEXT-FIRST: Ensure adequate space for text before scaling
            nodeSpacing: 120,
            rankSpacing: 140,
            padding: 40,
            diagramPadding: 40,
            subGraphTitleMargin: 20,
            titleTopMargin: 15,
            // CRITICAL: Allow text to determine node size
            arrowMarkerAbsolute: false,
            fontSize: 18,
            wrapEnabled: false, // Disable wrapping that causes cutoff
            wrap: false,
            align: 'center',
            direction: 'TB',
            // CRITICAL: Let text determine minimum node dimensions
            minNodeHeight: 100,
            minNodeWidth: 200
        },
        sequence: {
            useMaxWidth: true,
            wrap: false
        },
        gantt: {
            useMaxWidth: true
        }
    });

    // Render diagrams sequentially for better performance
    renderDiagramsSequentially();
}

// Render diagrams one by one for better performance and positioning
function renderDiagramsSequentially() {
    const diagramElements = document.querySelectorAll('.mermaid');
    let index = 0;
    
    function renderNext() {
        if (index >= diagramElements.length) {
            // All diagrams rendered, enhance interactivity
            setTimeout(enhanceDiagramInteractivity, 500);
            setTimeout(enhanceDiagramResponsiveness, 700);
            return;
        }
        
        const element = diagramElements[index];
        try {
            // Initialize mermaid for this element
            mermaid.init(undefined, element);
            
            index++;
            // Slight delay between diagram renders
            setTimeout(renderNext, 800);
        } catch (error) {
            console.warn(`Failed to render diagram ${index}:`, error);
            index++;
            setTimeout(renderNext, 100);
        }
    }
    
    renderNext();
}

// Enhanced diagram interactivity - MINIMAL INTERFERENCE
function enhanceDiagramInteractivity() {
    const diagrams = document.querySelectorAll('.mermaid svg');
    
    diagrams.forEach((diagram, diagramIndex) => {
        // MINIMAL: Only ensure basic responsive properties
        diagram.style.width = '100%';
        diagram.style.height = 'auto';
        diagram.style.overflow = 'visible';
        diagram.style.display = 'block';
        diagram.style.margin = '0 auto';
          // Add subtle loading completion effect
        diagram.style.opacity = '0';
        diagram.style.transition = 'opacity 0.5s ease-in-out';
          // Fade in the completed diagram
        setTimeout(() => {
            diagram.style.opacity = '1';
            // Apply edge coloring after diagram is fully rendered
            colorizeControlPlaneEdges(diagram);
            // CRITICAL: Fix text cutoff in deployment diagram
            fixDeploymentDiagramTextCutoff(diagram);
        }, diagramIndex * 200);
    });
}

// Colorize edges in the Control Plane diagram based on connection types
function colorizeControlPlaneEdges(svgElement) {
    const controlPlaneDiagram = document.getElementById('control-plane-diagram');
    if (!controlPlaneDiagram || !controlPlaneDiagram.contains(svgElement)) return;
    
    // Wait a bit more to ensure labels are rendered
    setTimeout(() => {
        const edgePaths = svgElement.querySelectorAll('.edgePath');
        const edgeLabels = svgElement.querySelectorAll('.edgeLabel');
        
        edgePaths.forEach((edgePath, index) => {
            const pathElement = edgePath.querySelector('path');
            if (!pathElement) return;
            
            // Find corresponding label
            const labelElement = edgeLabels[index];
            if (!labelElement) return;
            
            const labelText = labelElement.textContent || '';
            
            // Apply colors based on connection type
            if (labelText.includes('Policy') || labelText.includes('Rule') || labelText.includes('Metrics')) {
                // Control Plane connections - Blue
                pathElement.style.stroke = '#79c0ff';
                pathElement.style.filter = 'drop-shadow(0 2px 6px rgba(121, 192, 255, 0.4))';
            } else if (labelText.includes('Traffic') || labelText.includes('Network') || labelText.includes('Control')) {
                // Network connections - Purple
                pathElement.style.stroke = '#d2a8ff';
                pathElement.style.filter = 'drop-shadow(0 2px 6px rgba(210, 168, 255, 0.4))';
            } else if (labelText.includes('Model') || labelText.includes('Federated')) {
                // FL connections - Green
                pathElement.style.stroke = '#7ce38b';
                pathElement.style.filter = 'drop-shadow(0 2px 6px rgba(124, 227, 139, 0.4))';
            } else if (labelText.includes('Performance') || labelText.includes('Analysis')) {
                // Analysis connections - Pink
                pathElement.style.stroke = '#ffa7c4';
                pathElement.style.filter = 'drop-shadow(0 2px 6px rgba(255, 167, 196, 0.4))';
            }
            
            // Enhanced stroke width for all colored edges
            pathElement.style.strokeWidth = '2.5px';
            pathElement.style.transition = 'all 0.3s ease';
        });
    }, 300);
}

// FIXED: Enhanced diagram cleanup and positioning stability
function enhanceDiagramResponsiveness() {
    const diagrams = document.querySelectorAll('.mermaid svg');
    
    diagrams.forEach(diagram => {
        // FIXED: Clean up any problematic absolute positioning
        const nodes = diagram.querySelectorAll('.node, g.node');
        nodes.forEach(node => {
            // Remove any manually set positioning that could break layout
            if (node.style.position === 'absolute' || node.style.position === 'fixed') {
                node.style.position = 'static';
            }
            if (node.style.top !== '' || node.style.left !== '') {
                node.style.top = 'auto';
                node.style.left = 'auto';
                node.style.right = 'auto';
                node.style.bottom = 'auto';
            }
        });
        
        // FIXED: Add responsive scaling based on container size without breaking positioning
        const container = diagram.closest('.diagram-container');
        if (container) {
            const resizeObserver = new ResizeObserver(entries => {
                for (let entry of entries) {
                    const { width } = entry.contentRect;
                    
                    // FIXED: Apply responsive styles without forcing min-height
                    if (width < 768) {
                        diagram.style.fontSize = '12px';
                        // Let the diagram determine its own height
                    } else if (width < 1024) {
                        diagram.style.fontSize = '14px';
                    } else {
                        diagram.style.fontSize = '16px';
                    }
                }
            });
            resizeObserver.observe(container);
        }
    });
    
    // FIXED: Gentle layout recalculation for deployment diagram
    const deploymentDiagram = document.getElementById('deployment-diagram');
    if (deploymentDiagram) {
        setTimeout(() => {
            // Trigger a very subtle layout change to ensure proper rendering
            const mermaidSvg = deploymentDiagram.querySelector('.mermaid svg');
            if (mermaidSvg) {
                mermaidSvg.style.opacity = '0.99';
                setTimeout(() => {
                    mermaidSvg.style.opacity = '1';
                }, 50);
            }
        }, 100);
    }
}

// Smooth scrolling for navigation links
function initializeSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                const headerOffset = 80;
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Observe elements for scroll animations
function observeElements() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements that should animate in
    const elementsToObserve = document.querySelectorAll(
        '.feature-card, .solution-step, .diagram-container, .comparison-table, #roadmap .relative, .flopy-architecture-chart'
    );
    
    elementsToObserve.forEach(el => observer.observe(el));
}

// Performance monitoring
function initializePerformanceMonitoring() {
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log('Page load time:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
        });
    }
}

// Error handling
window.addEventListener('error', function(e) {
    console.warn('Page error:', e.error);
});

// Initialize performance monitoring
initializePerformanceMonitoring();

// Fix text cutoff specifically in deployment diagram
function fixDeploymentDiagramTextCutoff(svgElement) {
    const deploymentDiagram = document.getElementById('deployment-diagram');
    if (!deploymentDiagram || !deploymentDiagram.contains(svgElement)) return;
    
    // Wait for full rendering completion
    setTimeout(() => {
        // Fix all text elements within nodes
        const nodeGroups = svgElement.querySelectorAll('.node');
        nodeGroups.forEach(nodeGroup => {
            const textElements = nodeGroup.querySelectorAll('text');
            const rectElements = nodeGroup.querySelectorAll('rect');
            const polygonElements = nodeGroup.querySelectorAll('polygon');
            
            textElements.forEach(textElement => {
                // Measure actual text dimensions
                const bbox = textElement.getBBox();
                
                // Ensure text is fully visible by expanding parent containers
                textElement.style.overflow = 'visible';
                textElement.style.textAnchor = 'middle';
                textElement.style.dominantBaseline = 'central';
                
                // Find parent shape and expand if necessary
                rectElements.forEach(rect => {
                    const rectWidth = parseFloat(rect.getAttribute('width')) || 0;
                    const rectHeight = parseFloat(rect.getAttribute('height')) || 0;
                    
                    // Expand rectangle if text is wider than container
                    if (bbox.width > rectWidth * 0.8) {
                        const newWidth = Math.max(bbox.width * 1.3, rectWidth);
                        rect.setAttribute('width', newWidth);
                        // Adjust x position to keep centered
                        const currentX = parseFloat(rect.getAttribute('x')) || 0;
                        rect.setAttribute('x', currentX - (newWidth - rectWidth) / 2);
                    }
                    
                    if (bbox.height > rectHeight * 0.6) {
                        const newHeight = Math.max(bbox.height * 1.4, rectHeight);
                        rect.setAttribute('height', newHeight);
                        // Adjust y position to keep centered
                        const currentY = parseFloat(rect.getAttribute('y')) || 0;
                        rect.setAttribute('y', currentY - (newHeight - rectHeight) / 2);
                    }
                });
                
                // Handle polygons (for different node shapes)
                polygonElements.forEach(polygon => {
                    // Add padding to polygon points if text is too wide
                    const points = polygon.getAttribute('points');
                    if (points && bbox.width > 150) {
                        // Simple expansion by scaling points from center
                        const pointsArray = points.split(' ').map(point => {
                            const [x, y] = point.split(',').map(Number);
                            return [x * 1.2, y * 1.1]; // Expand horizontally more than vertically
                        });
                        const newPoints = pointsArray.map(([x, y]) => `${x},${y}`).join(' ');
                        polygon.setAttribute('points', newPoints);
                    }
                });
            });
            
            // Handle tspan elements within text
            const tspanElements = nodeGroup.querySelectorAll('tspan');
            tspanElements.forEach(tspan => {
                tspan.style.textAnchor = 'middle';
                tspan.style.dominantBaseline = 'central';
                tspan.style.overflow = 'visible';
            });
        });
        
        // Fix cluster/subgraph text
        const clusterGroups = svgElement.querySelectorAll('.cluster');
        clusterGroups.forEach(clusterGroup => {
            const clusterText = clusterGroup.querySelectorAll('text');
            const clusterRect = clusterGroup.querySelector('rect');
            
            clusterText.forEach(textElement => {
                const bbox = textElement.getBBox();
                textElement.style.overflow = 'visible';
                textElement.style.textAnchor = 'middle';
                
                // Expand cluster rectangle if text is too wide
                if (clusterRect && bbox.width > 0) {
                    const rectWidth = parseFloat(clusterRect.getAttribute('width')) || 0;
                    if (bbox.width > rectWidth * 0.9) {
                        const newWidth = Math.max(bbox.width * 1.2, rectWidth);
                        clusterRect.setAttribute('width', newWidth);
                        // Keep centered
                        const currentX = parseFloat(clusterRect.getAttribute('x')) || 0;
                        clusterRect.setAttribute('x', currentX - (newWidth - rectWidth) / 2);
                    }
                }
            });
        });
        
        // Force SVG to recalculate its viewBox
        const viewBox = svgElement.getAttribute('viewBox');
        if (viewBox) {
            const [x, y, width, height] = viewBox.split(' ').map(Number);
            // Expand viewBox to accommodate larger nodes
            const newViewBox = `${x - 50} ${y - 50} ${width + 100} ${height + 100}`;
            svgElement.setAttribute('viewBox', newViewBox);
        }
        
    }, 500); // Wait 500ms for full rendering
}
