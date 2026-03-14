/**
 * DaemonStatusOverlay — Cinematic daemon connection ceremony
 * ===========================================================
 * Shows a dramatic fullscreen overlay when the daemon first connects,
 * with a glitch-style reveal and particle burst effect.
 */

import { useEffect, useState } from "react";
import { Shield, Wifi, CheckCircle2 } from "lucide-react";

interface DaemonStatusOverlayProps {
    daemonConnected: boolean;
    sessionId: string;
}

export function DaemonStatusOverlay({ daemonConnected, sessionId }: DaemonStatusOverlayProps) {
    const [showCeremony, setShowCeremony] = useState(false);
    const [ceremonyPhase, setCeremonyPhase] = useState(0);
    const [hasShownOnce, setHasShownOnce] = useState(false);

    useEffect(() => {
        if (daemonConnected && !hasShownOnce) {
            setShowCeremony(true);
            setHasShownOnce(true);

            // Phase 1: Shield icon
            setCeremonyPhase(1);

            // Phase 2: "Encrypting Connection"
            const t1 = setTimeout(() => setCeremonyPhase(2), 800);

            // Phase 3: "Daemon Linked"
            const t2 = setTimeout(() => setCeremonyPhase(3), 1600);

            // Phase 4: Success + fade out
            const t3 = setTimeout(() => setCeremonyPhase(4), 2400);

            // Dismiss
            const t4 = setTimeout(() => setShowCeremony(false), 3200);

            return () => {
                clearTimeout(t1);
                clearTimeout(t2);
                clearTimeout(t3);
                clearTimeout(t4);
            };
        }
    }, [daemonConnected, hasShownOnce]);

    if (!showCeremony) return null;

    return (
        <div
            className={`fixed inset-0 z-[200] flex items-center justify-center transition-opacity duration-500 ${ceremonyPhase >= 4 ? "opacity-0 pointer-events-none" : "opacity-100"}`}
            style={{
                background: "radial-gradient(circle at center, rgba(14, 165, 233, 0.08) 0%, rgba(0,0,0,0.92) 70%)",
                backdropFilter: "blur(8px)",
            }}
        >
            {/* Central animation container */}
            <div className="flex flex-col items-center gap-6 text-center">
                {/* Animated icon ring */}
                <div className="relative">
                    {/* Outer pulsing ring */}
                    <div
                        className={`absolute inset-0 rounded-full transition-all duration-700 ${ceremonyPhase >= 3 ? "scale-[2] opacity-0" : "scale-100 opacity-100"}`}
                        style={{
                            background: "conic-gradient(from 0deg, transparent, rgba(56,189,248,0.4), transparent)",
                            animation: "spin 2s linear infinite",
                            width: "120px",
                            height: "120px",
                            margin: "-20px",
                        }}
                    />

                    {/* Icon */}
                    <div
                        className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-500 ${ceremonyPhase >= 3
                            ? "bg-emerald-500/20 border-emerald-500/50 shadow-[0_0_40px_rgba(16,185,129,0.4)]"
                            : "bg-sky-500/20 border-sky-500/50 shadow-[0_0_40px_rgba(56,189,248,0.3)]"
                            } border-2`}
                    >
                        {ceremonyPhase < 2 && <Shield className="w-10 h-10 text-sky-400 animate-pulse" />}
                        {ceremonyPhase === 2 && <Wifi className="w-10 h-10 text-sky-400 animate-pulse" />}
                        {ceremonyPhase >= 3 && <CheckCircle2 className="w-10 h-10 text-emerald-400" />}
                    </div>
                </div>

                {/* Status text */}
                <div className="space-y-2">
                    <div
                        className={`text-lg font-semibold tracking-wide transition-all duration-300 ${ceremonyPhase >= 3 ? "text-emerald-400" : "text-sky-400"}`}
                    >
                        {ceremonyPhase <= 1 && "Establishing Secure Bridge..."}
                        {ceremonyPhase === 2 && "Encrypting MCP Tunnel..."}
                        {ceremonyPhase >= 3 && "✓ Daemon Linked Successfully"}
                    </div>

                    {/* Terminal-style connection log */}
                    <div className="font-mono text-[11px] text-white/40 space-y-0.5 max-w-xs">
                        <div className={`transition-opacity duration-200 ${ceremonyPhase >= 1 ? "opacity-100" : "opacity-0"}`}>
                            <span className="text-sky-500">$</span> nora handshake --id {sessionId}
                        </div>
                        <div className={`transition-opacity duration-200 ${ceremonyPhase >= 2 ? "opacity-100" : "opacity-0"}`}>
                            <span className="text-emerald-500">→</span> mcp_bridge: websocket connected
                        </div>
                        <div className={`transition-opacity duration-200 ${ceremonyPhase >= 3 ? "opacity-100" : "opacity-0"}`}>
                            <span className="text-emerald-500">→</span> tools: {"{"}kill_process, toggle_bluetooth, manage_service, ...{"}"} loaded
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
