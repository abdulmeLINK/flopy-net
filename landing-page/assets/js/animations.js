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

/**
// GSAP ScrollTrigger animations for FLOPY-NET landing page

document.addEventListener('DOMContentLoaded', function() {
    // Wait for GSAP to be available
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
        setTimeout(() => document.dispatchEvent(new Event('DOMContentLoaded')), 100);
        return;
    }
    
    initializeScrollAnimations();
    initializePrimerAnimations();
    initializeSolutionAnimations();
    initializeFeatureAnimations();
});

function initializeScrollAnimations() {    // Hero section entrance animation with parallax (40% faster)
    gsap.from('#hero .relative > div', {
        duration: 1.08, // 1.8 * 0.6 = 1.08
        y: 60,
        opacity: 0,
        ease: 'power3.out',
        delay: 0.36 // 0.6 * 0.6 = 0.36
    });
    
    // Navigation fade in (40% faster)
    gsap.from('nav', {
        duration: 0.72, // 1.2 * 0.6 = 0.72
        y: -30,
        opacity: 0,
        ease: 'power2.out'
    });
      // Enhanced pulse button animation (40% faster)
    gsap.to('#pulse-button', {
        scale: 1.02,
        duration: 0.6, // 1 * 0.6 = 0.6
        yoyo: true,
        repeat: -1,
        ease: 'power2.inOut'
    });
    
    // Parallax effect for hero background
    gsap.to('#network-animation', {
        scrollTrigger: {
            trigger: '#hero',
            start: 'top top',
            end: 'bottom top',
            scrub: 1
        },
        y: -100,
        opacity: 0.5,
        ease: 'none'
    });
      // Section reveal animations with stagger (40% faster)
    gsap.utils.toArray('section:not(#hero)').forEach((section, index) => {
        gsap.from(section, {
            scrollTrigger: {
                trigger: section,
                start: 'top 85%',
                end: 'bottom 15%',
                toggleActions: 'play none none reverse'
            },
            duration: 0.72, // 1.2 * 0.6 = 0.72
            y: 40,
            opacity: 0,
            ease: 'power2.out',
            delay: index * 0.06 // 0.1 * 0.6 = 0.06
        });
    });
}

function initializePrimerAnimations() {
    // Centralized learning animation
    createCentralizedAnimation();
    
    // Federated learning animation
    createFederatedAnimation();
    
    // Chaos animation
    createChaosAnimation();
      // Text animations for primer sections (40% faster)
    gsap.utils.toArray('#primer h2').forEach((heading, index) => {
        gsap.from(heading, {
            scrollTrigger: {
                trigger: heading,
                start: 'top 80%',
                end: 'bottom 20%',
                toggleActions: 'play none none reverse'
            },
            duration: 0.6, // 1 * 0.6 = 0.6
            x: index % 2 === 0 ? -50 : 50,
            opacity: 0,
            ease: 'power2.out'
        });
    });
    
    gsap.utils.toArray('#primer p').forEach((paragraph, index) => {
        gsap.from(paragraph, {
            scrollTrigger: {
                trigger: paragraph,
                start: 'top 85%',
                end: 'bottom 15%',
                toggleActions: 'play none none reverse'
            },
            duration: 0.6, // 1 * 0.6 = 0.6
            y: 30,
            opacity: 0,
            ease: 'power2.out',
            delay: 0.12 // 0.2 * 0.6 = 0.12
        });
    });
}

function createCentralizedAnimation() {
    const container = document.getElementById('centralized-animation');
    if (!container) return;
    
    // Create animation elements
    const users = [];
    const server = createAnimationElement('🖥️', '40px', container);
    server.style.position = 'absolute';
    server.style.top = '50%';
    server.style.left = '50%';
    server.style.transform = 'translate(-50%, -50%)';
    
    // Create user devices around the server
    const userPositions = [
        { top: '20%', left: '20%' },
        { top: '20%', right: '20%' },
        { top: '80%', left: '20%' },
        { top: '80%', right: '20%' }
    ];
    
    userPositions.forEach((pos, index) => {
        const user = createAnimationElement('📱', '30px', container);
        user.style.position = 'absolute';
        Object.assign(user.style, pos);
        users.push(user);
    });
    
    // Animate data packets flowing to server
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 1 });
    
    users.forEach((user, index) => {
        const packet = createAnimationElement('📦', '20px', container);
        packet.style.position = 'absolute';
        packet.style.opacity = '0';
        
        // Position packet at user location initially
        const userRect = user.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        packet.style.left = (userRect.left - containerRect.left) + 'px';
        packet.style.top = (userRect.top - containerRect.top) + 'px';
        
        tl.to(packet, {
            opacity: 1,
            duration: 0.3,
            delay: index * 0.2
        }, 0)
        .to(packet, {
            left: '50%',
            top: '50%',
            duration: 1,
            ease: 'power2.inOut'
        }, index * 0.2)
        .to(packet, {
            opacity: 0,
            duration: 0.3
        }, index * 0.2 + 1);
    });
    
    // Server glow effect when receiving data
    tl.to(server, {
        filter: 'drop-shadow(0 0 10px #00D4FF)',
        duration: 0.5,
        yoyo: true,
        repeat: 1,
        ease: 'power2.inOut'
    }, 1);
}

function createFederatedAnimation() {
    const container = document.getElementById('federated-animation');
    if (!container) return;
    
    // Create animation elements
    const server = createAnimationElement('🖥️', '40px', container);
    server.style.position = 'absolute';
    server.style.top = '50%';
    server.style.left = '50%';
    server.style.transform = 'translate(-50%, -50%)';
    
    const userPositions = [
        { top: '20%', left: '20%' },
        { top: '20%', right: '20%' },
        { top: '80%', left: '20%' },
        { top: '80%', right: '20%' }
    ];
    
    const users = userPositions.map((pos, index) => {
        const user = createAnimationElement('📱', '30px', container);
        user.style.position = 'absolute';
        Object.assign(user.style, pos);
        return user;
    });
    
    // Animate model updates flowing from server
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 1 });
    
    users.forEach((user, index) => {
        const update = createAnimationElement('⚙️', '20px', container);
        update.style.position = 'absolute';
        update.style.opacity = '0';
        update.style.left = '50%';
        update.style.top = '50%';
        
        const userRect = user.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const targetLeft = (userRect.left - containerRect.left) + 'px';
        const targetTop = (userRect.top - containerRect.top) + 'px';
        
        tl.to(update, {
            opacity: 1,
            duration: 0.3,
            delay: index * 0.2
        }, 0)
        .to(update, {
            left: targetLeft,
            top: targetTop,
            duration: 1,
            ease: 'power2.inOut'
        }, index * 0.2)
        .to(update, {
            opacity: 0,
            duration: 0.3
        }, index * 0.2 + 1);
    });
}

function createChaosAnimation() {
    const container = document.getElementById('chaos-animation');
    if (!container) return;
    
    // Create animation elements similar to federated
    const server = createAnimationElement('🖥️', '40px', container);
    server.style.position = 'absolute';
    server.style.top = '50%';
    server.style.left = '50%';
    server.style.transform = 'translate(-50%, -50%)';
    
    const userPositions = [
        { top: '20%', left: '20%' },
        { top: '20%', right: '20%' },
        { top: '80%', left: '20%' },
        { top: '80%', right: '20%' }
    ];
    
    const users = userPositions.map((pos, index) => {
        const user = createAnimationElement('📱', '30px', container);
        user.style.position = 'absolute';
        Object.assign(user.style, pos);
        return user;
    });
      // More chaotic animation with VERY obvious packet loss and delays
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.1 }); // Even faster repeat - was 0.2
      users.forEach((user, index) => {
        // FIXED: Create update packets going FROM client TO server (not server to client)
        const update = createAnimationElement('⚙️', '20px', container);
        update.style.position = 'absolute';
        update.style.opacity = '0';
        // FIXED: Start from client position, not server
        const userRect = user.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        update.style.left = (userRect.left - containerRect.left) + 'px';
        update.style.top = (userRect.top - containerRect.top) + 'px';
        update.classList.add('animation-node'); // Add class for CSS styling
        
        const serverRect = server.getBoundingClientRect();
        const targetLeft = (serverRect.left - containerRect.left) + 'px';
        const targetTop = (serverRect.top - containerRect.top) + 'px';
        
        // VERY obvious failures - 60% failure rate (increased from 50%)
        const fails = Math.random() < 0.6;
        const delay = Math.random() * 1.0; // Even shorter random delay
          if (fails) {
            tl.to(update, {
                opacity: 1,
                duration: 0.15, // Even faster appear
                delay: index * 0.1 + delay,
                onComplete: () => update.classList.add('failed')
            }, 0)
            .to(update, {
                left: targetLeft,
                top: targetTop,
                duration: 0.3, // Faster movement
                ease: 'power2.out'
            }, index * 0.1 + delay)            .to(update, {
                backgroundColor: '#ff1111', // Even brighter red
                scale: 1.0, // Reduced from 1.8 to make 60% smaller (1.8 * 0.6 ≈ 1.0)
                duration: 0.1,
                onStart: () => {
                    update.textContent = '💥'; // Change to explosion emoji
                    update.style.fontSize = '18px'; // Reduced from 28px to make 60% smaller
                    // Add dramatic packet drop trail effect
                    createPacketDropEffect(update, container);
                }
            }, index * 0.1 + delay + 0.15)
            .to(update, {
                scale: 0,
                opacity: 0,
                rotation: 180, // Add rotation for more drama
                duration: 0.3 // More dramatic disappear
            }, index * 0.1 + delay + 0.25);
        }else {
            // Even successful updates have some jitter to show instability
            tl.to(update, {
                opacity: 1,
                duration: 0.15,
                delay: index * 0.1 + delay,
                onComplete: () => update.classList.add('recovering')
            }, 0)
            .to(update, {
                left: targetLeft,
                top: targetTop,
                duration: 0.6 + delay,
                ease: 'power2.inOut',
                // Add some jitter even to successful updates
                x: `+=${Math.random() * 20 - 10}`,
                y: `+=${Math.random() * 20 - 10}`
            }, index * 0.1 + delay)
            .to(update, {
                opacity: 0,
                scale: 0.8,
                duration: 0.15
            }, index * 0.1 + delay + 0.6);
        }
    });
}

function initializeSolutionAnimations() {
    // Solution steps stagger animation
    gsap.utils.toArray('.solution-step').forEach((step, index) => {
        gsap.from(step, {
            scrollTrigger: {
                trigger: step,
                start: 'top 80%',
                end: 'bottom 20%',
                toggleActions: 'play none none reverse'
            },
            duration: 0.8,
            y: 50,
            opacity: 0,
            ease: 'power2.out',
            delay: index * 0.2
        });
    });
    
    // Solution section title
    gsap.from('#solution h2', {
        scrollTrigger: {
            trigger: '#solution h2',
            start: 'top 80%',
            end: 'bottom 20%',
            toggleActions: 'play none none reverse'
        },
        duration: 1,
        y: 30,
        opacity: 0,
        ease: 'power2.out'
    });
}

function initializeFeatureAnimations() {
    // Feature cards stagger animation
    gsap.utils.toArray('.feature-card').forEach((card, index) => {
        gsap.from(card, {
            scrollTrigger: {
                trigger: card,
                start: 'top 85%',
                end: 'bottom 15%',
                toggleActions: 'play none none reverse'
            },
            duration: 0.8,
            y: 40,
            opacity: 0,
            ease: 'power2.out',
            delay: index * 0.1
        });
    });
      // Architecture section animations
    gsap.utils.toArray('.diagram-container').forEach((container, index) => {
        gsap.from(container, {
            scrollTrigger: {
                trigger: container,
                start: 'top 85%',
                end: 'bottom 15%',
                toggleActions: 'play none none reverse'
            },
            duration: 1.2,
            scale: 0.95,
            opacity: 0,
            y: 40,
            ease: 'power2.out',
            delay: index * 0.2
        });
    });
    
    // Diagram header animations
    gsap.utils.toArray('.diagram-header').forEach((header, index) => {
        gsap.from(header.querySelector('.diagram-title'), {
            scrollTrigger: {
                trigger: header,
                start: 'top 90%',
                end: 'bottom 10%',
                toggleActions: 'play none none reverse'
            },
            duration: 1,
            y: 30,
            opacity: 0,
            ease: 'power2.out'
        });
        
        gsap.from(header.querySelector('.diagram-description'), {
            scrollTrigger: {
                trigger: header,
                start: 'top 90%',
                end: 'bottom 10%',
                toggleActions: 'play none none reverse'
            },
            duration: 1,
            y: 20,
            opacity: 0,
            ease: 'power2.out',
            delay: 0.2
        });
    });
}

// Utility function to create animation elements
function createAnimationElement(content, size, container) {
    const element = document.createElement('div');
    element.textContent = content;
    element.style.fontSize = size;
    element.style.userSelect = 'none';
    element.style.pointerEvents = 'none';
    container.appendChild(element);
    return element;
}

// Create dramatic packet drop effect for failed transmissions
function createPacketDropEffect(failedElement, container) {
    // Create multiple debris particles
    for (let i = 0; i < 6; i++) {
        const debris = createAnimationElement('💫', '12px', container); // Reduced from 16px to make 60% smaller
        debris.style.position = 'absolute';
        debris.style.left = failedElement.style.left;
        debris.style.top = failedElement.style.top;
        debris.style.opacity = '0.8';
        debris.style.color = '#ff4444';
        debris.style.zIndex = '999';
        
        // Random direction for debris
        const angle = (i / 6) * Math.PI * 2;
        const distance = 40 + Math.random() * 30;
        const targetX = Math.cos(angle) * distance;
        const targetY = Math.sin(angle) * distance;
        
        // Animate debris explosion
        gsap.to(debris, {
            x: targetX,
            y: targetY,
            rotation: Math.random() * 360,
            scale: 0.3,
            opacity: 0,
            duration: 0.8,
            ease: 'power2.out',
            onComplete: () => debris.remove()
        });
    }
    
    // Create network disruption waves
    const wave = createAnimationElement('🌊', '16px', container); // Reduced from 24px to make 60% smaller
    wave.style.position = 'absolute';
    wave.style.left = failedElement.style.left;
    wave.style.top = failedElement.style.top;
    wave.style.opacity = '0.6';
    wave.style.color = '#ff6666';
    wave.style.zIndex = '998';
    
    gsap.to(wave, {
        scale: 3.0, // Reduced from 4 to make 60% smaller
        opacity: 0,
        duration: 1.2,
        ease: 'power2.out',
        onComplete: () => wave.remove()
    });
}

// Refresh ScrollTrigger on window resize
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        ScrollTrigger.refresh();
    }, 250);
});
