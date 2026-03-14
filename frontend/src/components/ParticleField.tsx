/**
 * ParticleField — Animated floating particle background
 * =====================================================
 * Creates a cinematic particle field effect using canvas.
 * Particles slowly drift and connect with nearby particles
 * via faint lines, creating a "neural network" aesthetic.
 */

import { useEffect, useRef } from "react";

interface Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    size: number;
    opacity: number;
}

export function ParticleField({ particleCount = 60, color = "56, 189, 248" }: { particleCount?: number; color?: string }) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animationId: number;
        let particles: Particle[] = [];

        const resize = () => {
            canvas.width = canvas.offsetWidth * window.devicePixelRatio;
            canvas.height = canvas.offsetHeight * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        };

        const initParticles = () => {
            particles = Array.from({ length: particleCount }, () => ({
                x: Math.random() * canvas.offsetWidth,
                y: Math.random() * canvas.offsetHeight,
                vx: (Math.random() - 0.5) * 0.3,
                vy: (Math.random() - 0.5) * 0.3,
                size: Math.random() * 1.5 + 0.5,
                opacity: Math.random() * 0.5 + 0.1,
            }));
        };

        const draw = () => {
            ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);

            // Draw connections
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 120) {
                        const alpha = (1 - dist / 120) * 0.15;
                        ctx.strokeStyle = `rgba(${color}, ${alpha})`;
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }

            // Draw and move particles
            for (const p of particles) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${color}, ${p.opacity})`;
                ctx.fill();

                p.x += p.vx;
                p.y += p.vy;

                // Wrap around edges
                if (p.x < 0) p.x = canvas.offsetWidth;
                if (p.x > canvas.offsetWidth) p.x = 0;
                if (p.y < 0) p.y = canvas.offsetHeight;
                if (p.y > canvas.offsetHeight) p.y = 0;
            }

            animationId = requestAnimationFrame(draw);
        };

        resize();
        initParticles();
        draw();

        window.addEventListener("resize", () => {
            resize();
            initParticles();
        });

        return () => {
            cancelAnimationFrame(animationId);
            window.removeEventListener("resize", resize);
        };
    }, [particleCount, color]);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
            style={{ opacity: 0.6 }}
        />
    );
}
