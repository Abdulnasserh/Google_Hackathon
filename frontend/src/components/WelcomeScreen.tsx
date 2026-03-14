/**
 * WelcomeScreen — Shown when there are no messages yet
 * =====================================================
 * Hero section with capability cards and suggestion chips.
 * Updated to reflect Nora's autonomous technician capabilities.
 */

import { Eye, Ear, MonitorSmartphone, Zap, DownloadCloud, Wrench, Cpu, Shield } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";

interface WelcomeScreenProps {
    isConnected: boolean;
    onSendText: (text: string) => void;
    onConnect: () => void;
}

const CAPABILITIES = [
    {
        icon: <Eye className="h-5 w-5" />,
        label: "See",
        desc: "Share screenshots or capture your screen for instant analysis",
        color: "from-emerald-500 to-teal-500",
        shadow: "shadow-emerald-500/20",
    },
    {
        icon: <Ear className="h-5 w-5" />,
        label: "Hear",
        desc: "Speak naturally — I understand your voice in real time",
        color: "from-sky-500 to-blue-500",
        shadow: "shadow-sky-500/20",
    },
    {
        icon: <Wrench className="h-5 w-5" />,
        label: "Fix",
        desc: "I autonomously diagnose AND fix issues on your machine",
        color: "from-indigo-500 to-violet-500",
        shadow: "shadow-indigo-500/20",
    },
];

const SUGGESTIONS = [
    { icon: "🔧", text: "Fix my Bluetooth — it won't connect" },
    { icon: "📶", text: "My Wi-Fi keeps disconnecting, fix it" },
    { icon: "🔇", text: "No sound from my speakers" },
    { icon: "🐌", text: "My PC is slow, kill what's hogging it" },
    { icon: "🖨️", text: "Printer is stuck, clear the queue" },
    { icon: "💾", text: "I'm running out of disk space" },
];

export function WelcomeScreen({ isConnected, onSendText, onConnect }: WelcomeScreenProps) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-10 py-8">

            {/* ── Hero ── */}
            <div className="text-center space-y-4">
                <div className="relative inline-flex items-center justify-center">
                    {/* Glow ring */}
                    <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-sky-500/30 to-indigo-600/30 blur-2xl scale-150" />
                    <div className="relative h-24 w-24 rounded-3xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-2xl shadow-sky-500/30 animate-glow-pulse">
                        <MonitorSmartphone className="h-12 w-12 text-white" />
                    </div>
                </div>

                <div className="space-y-2 pt-1">
                    <h2 className="text-3xl font-bold tracking-tight gradient-text-premium">
                        Nora — AI Live Technician
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
                        I don't just diagnose — I <strong className="text-sky-400">autonomously fix</strong> your 
                        computer. Tell me the problem and watch me work.
                    </p>
                    <div className="flex items-center justify-center gap-4 mt-3">
                        <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/70">
                            <Shield className="w-3 h-3" /> Diagnose
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] text-sky-400/70">
                            <Wrench className="w-3 h-3" /> Fix
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] text-violet-400/70">
                            <Cpu className="w-3 h-3" /> Control
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Capability Cards ── */}
            <div className="flex gap-3 max-w-lg w-full">
                {CAPABILITIES.map((cap, i) => (
                    <div
                        key={i}
                        className="flex-1 glass-card-premium p-4 text-center space-y-2.5 hover:border-white/10 transition-all duration-300 group"
                        style={{ animationDelay: `${i * 100}ms` }}
                    >
                        <div
                            className={`h-11 w-11 rounded-xl bg-gradient-to-br ${cap.color} flex items-center justify-center mx-auto text-white shadow-lg ${cap.shadow} group-hover:scale-110 transition-transform duration-300`}
                        >
                            {cap.icon}
                        </div>
                        <p className="text-xs font-semibold tracking-wide uppercase text-foreground/80">
                            {cap.label}
                        </p>
                        <p className="text-[11px] text-muted-foreground leading-snug">
                            {cap.desc}
                        </p>
                    </div>
                ))}
            </div>

            <Separator className="max-w-xs opacity-30" />

            {/* ── Connected: Suggestion Chips ── */}
            {isConnected ? (
                <div className="w-full max-w-md space-y-3">
                    <p className="text-center text-[11px] text-muted-foreground uppercase tracking-widest font-medium">
                        Tell me what to fix
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                        {SUGGESTIONS.map((s, i) => (
                            <Card
                                key={i}
                                onClick={() => onSendText(s.text)}
                                className="group cursor-pointer hover:border-sky-500/40 hover:bg-sky-500/5 transition-all duration-200 hover:shadow-md hover:shadow-sky-500/10 py-0"
                            >
                                <div className="px-3 py-2.5 flex items-center gap-2.5">
                                    <span className="text-base shrink-0">{s.icon}</span>
                                    <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors leading-tight">
                                        {s.text}
                                    </span>
                                </div>
                            </Card>
                        ))}
                    </div>
                </div>
            ) : (
                /* ── Disconnected: CTA ── */
                <div className="flex flex-col items-center gap-3">
                    <Badge
                        variant="outline"
                        className="text-xs border-amber-500/30 text-amber-400 py-1.5 px-4 gap-2"
                    >
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse inline-block" />
                        Click Connect to start your session
                    </Badge>
                    <Button
                        onClick={onConnect}
                        className="bg-gradient-to-r from-sky-500 to-indigo-600 text-white hover:from-sky-400 hover:to-indigo-500 shadow-lg shadow-sky-500/25 gap-2"
                    >
                        <Zap className="h-4 w-4" />
                        Connect Now
                    </Button>

                    <div className="mt-8 flex flex-col items-center gap-3">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium uppercase tracking-widest">
                            <DownloadCloud className="h-4 w-4" />
                            Diagnostic Daemon
                        </div>
                        <p className="text-[11px] text-muted-foreground max-w-[280px] text-center leading-snug">
                            Nora needs a lightweight daemon running on your machine to diagnose <strong>and fix</strong> issues remotely and securely.
                        </p>
                        <div className="flex gap-2">
                            <a href="https://github.com/Abdulnasserh/Google_Hackathon/actions" target="_blank" rel="noopener noreferrer" className="text-xs text-sky-400 hover:text-sky-300 transition-colors bg-sky-500/10 px-3 py-1.5 rounded-md hover:bg-sky-500/20">
                                Windows
                            </a>
                            <a href="https://github.com/Abdulnasserh/Google_Hackathon/actions" target="_blank" rel="noopener noreferrer" className="text-xs text-sky-400 hover:text-sky-300 transition-colors bg-sky-500/10 px-3 py-1.5 rounded-md hover:bg-sky-500/20">
                                Mac (Intel)
                            </a>
                            <a href="https://github.com/Abdulnasserh/Google_Hackathon/actions" target="_blank" rel="noopener noreferrer" className="text-xs text-sky-400 hover:text-sky-300 transition-colors bg-sky-500/10 px-3 py-1.5 rounded-md hover:bg-sky-500/20">
                                Mac (Apple Silicon)
                            </a>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
