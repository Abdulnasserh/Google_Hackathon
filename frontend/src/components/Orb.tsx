import React from "react";

interface OrbProps {
    isActive?: boolean;
}

export function Orb({ isActive = false }: OrbProps) {
    return (
        <div className="relative w-64 h-64 md:w-80 md:h-80 flex items-center justify-center mx-auto my-8">
            {/* Outer Glow */}
            <div
                className={`absolute inset-0 rounded-full blur-3xl opacity-40 transition-all duration-1000 ${isActive ? "bg-purple-500/60 scale-110" : "bg-sky-500/40 scale-100"
                    }`}
            />

            {/* Core Sphere Area - CSS Mesh Simulation */}
            <div className={`relative w-full h-full rounded-full overflow-hidden transition-all duration-700 ease-in-out ${isActive ? "animate-[glow-pulse_2s_ease-in-out_infinite]" : ""}`}>
                {/* We combine multiple borders and rotations to simulate a wireframe sphere */}
                <div className="absolute inset-0 rounded-full border-4 border-indigo-500/30 rotate-45 animate-[spin_8s_linear_infinite]" />
                <div className="absolute inset-0 rounded-full border-4 border-purple-500/30 -rotate-45 animate-[spin_12s_linear_infinite_reverse]" />
                <div className="absolute inset-4 rounded-full border-4 border-sky-400/30 rotate-90 animate-[spin_10s_linear_infinite]" />
                <div className="absolute inset-8 rounded-full border-4 border-fuchsia-400/20 rotate-180 animate-[spin_15s_linear_infinite_reverse]" />
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-transparent via-purple-900/20 to-indigo-900/40 backdrop-blur-[2px]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.1),transparent_70%)] rounded-full" />
            </div>

            {isActive && (
                <div className="absolute inset-0 rounded-full border border-purple-400/50 shadow-[0_0_20px_rgba(168,85,247,0.5)] animate-pulse" />
            )}
        </div>
    );
}
