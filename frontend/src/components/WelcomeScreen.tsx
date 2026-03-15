/**
 * WelcomeScreen — Shown when there are no messages yet
 * =====================================================
 * Hero section with capability cards and suggestion chips.
 * Updated to reflect Nora's expanded autonomous assistant capabilities.
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
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-10 py-8 relative">
            {/* Ambient Watermark */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none overflow-hidden z-0 opacity-10">
                <span className="text-[30vw] font-black text-sky-500/[0.05] tracking-[0.2em] transform rotate-3">NORA</span>
            </div>

            {/* ── Hero ── */}
            <div className="text-center space-y-4 relative z-10">
                <div className="relative inline-flex items-center justify-center">
                    {/* Glow ring */}
                    <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-sky-500/30 to-indigo-600/30 blur-2xl scale-150" />
                    <div className="relative h-24 w-24 rounded-3xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-2xl shadow-sky-500/30 animate-glow-pulse">
                        <MonitorSmartphone className="h-12 w-12 text-white" />
                    </div>
                </div>

                <div className="space-y-2 pt-1 border-t border-white/5 mt-4 pt-6">
                    <h2 className="text-4xl font-black tracking-[0.15em] gradient-text uppercase">
                        NORA
                    </h2>
                    <p className="text-xs text-sky-400 font-bold uppercase tracking-[0.3em] opacity-60 mb-4">Personal AI Assistant</p>
                    <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
                        I am your autonomous companion. I write code, manage documents, 
                        and <strong className="text-sky-400">directly control</strong> your 
                        computer to get things done.
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

                    <div className="mt-8 flex flex-col items-center gap-4 w-full max-w-sm">
                        <div className="flex items-center gap-2 text-xs text-sky-400 font-bold uppercase tracking-[0.2em]">
                            <Zap className="h-4 w-4 animate-pulse" />
                            Bridge the Gap
                        </div>
                        
                        <div className="glass-card-premium p-5 border-sky-500/20 bg-sky-500/5 space-y-3 relative overflow-hidden group">
                            {/* Decorative background glow */}
                            <div className="absolute -top-10 -right-10 w-24 h-24 bg-sky-500/10 blur-2xl rounded-full" />
                            
                            <p className="text-[12px] text-foreground font-semibold leading-tight">
                                Nora is a "ghost in the shell." Give her a body to act.
                            </p>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                To unlock Nora's ability to <span className="text-sky-400 font-medium">autonomously fix</span> your machine, you'll need the Nora Daemon. 
                                It's a secure, lightweight bridge that lets Nora's intelligence touch your hardware.
                            </p>

                            <Separator className="bg-white/5" />

                            <div className="space-y-2 pt-1">
                                <p className="text-[9px] uppercase tracking-wider text-muted-foreground font-bold">Recommended for your {(() => {
                                    const ua = navigator.userAgent;
                                    if (ua.includes("Win")) return "Windows PC";
                                    if (ua.includes("Mac")) return "Mac";
                                    return "Device";
                                })()}:</p>
                                
                                <div className="flex flex-wrap gap-2">
                                    {navigator.userAgent.includes("Win") ? (
                                        <Button asChild size="sm" className="h-8 bg-sky-600 hover:bg-sky-500 text-white border-none shadow-lg shadow-sky-900/40">
                                            <a href="https://github.com/Abdulnasserh/Google_Hackathon/releases/tag/NORA-DAEMONS" target="_blank" rel="noopener noreferrer">
                                                <DownloadCloud className="w-3.5 h-3.5 mr-2" />
                                                Download for Windows
                                            </a>
                                        </Button>
                                    ) : (
                                        <>
                                            <Button asChild size="sm" className="h-8 bg-indigo-600 hover:bg-indigo-500 text-white border-none shadow-lg shadow-indigo-900/40">
                                                <a href="https://github.com/Abdulnasserh/Google_Hackathon/releases/tag/NORA-DAEMONS" target="_blank" rel="noopener noreferrer">
                                                    <DownloadCloud className="w-3.5 h-3.5 mr-2" />
                                                    Mac (Apple Silicon)
                                                </a>
                                            </Button>
                                            <Button asChild variant="outline" size="sm" className="h-8 border-white/10 hover:bg-white/5 text-muted-foreground hover:text-foreground">
                                                <a href="https://github.com/Abdulnasserh/Google_Hackathon/releases/tag/NORA-DAEMONS" target="_blank" rel="noopener noreferrer">
                                                    <DownloadCloud className="w-3.5 h-3.5 mr-2" />
                                                    Mac (Intel)
                                                </a>
                                            </Button>
                                        </>
                                    )}
                                </div>
                            </div>
                            
                            <p className="text-[9px] text-muted-foreground/60 italic pt-1">
                                Secure. Sandboxed. Open Source. Nora only runs whitelisted commands you can see in the log.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
