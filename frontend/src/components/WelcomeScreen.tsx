/**
 * WelcomeScreen — Shown when there are no messages yet
 * =====================================================
 * Hero section with capability cards and suggestion chips.
 */

import { Eye, Ear, MessageSquare, MonitorSmartphone, Zap, DownloadCloud } from "lucide-react";
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
        icon: <MessageSquare className="h-5 w-5" />,
        label: "Speak",
        desc: "I reply with voice & step-by-step text instructions",
        color: "from-indigo-500 to-violet-500",
        shadow: "shadow-indigo-500/20",
    },
];

const SUGGESTIONS = [
    { icon: "🖥️", text: "My PC is running very slow" },
    { icon: "📶", text: "Wi-Fi keeps disconnecting" },
    { icon: "🔵", text: "I'm getting a Blue Screen error" },
    { icon: "🔊", text: "No sound from my speakers" },
    { icon: "🖨️", text: "Printer won't connect" },
    { icon: "🔒", text: "I think I have a virus" },
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
                    <h2 className="text-3xl font-bold tracking-tight gradient-text">
                        Nora — AI Live Technician
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
                        Speak, type, or share a screenshot — I'll guide you through
                        step-by-step solutions in real time.
                    </p>
                </div>
            </div>

            {/* ── Capability Cards ── */}
            <div className="flex gap-3 max-w-lg w-full">
                {CAPABILITIES.map((cap, i) => (
                    <div
                        key={i}
                        className="flex-1 glass-card p-4 text-center space-y-2.5 hover:border-white/10 transition-all duration-300 group"
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
                        Try asking
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
                        <p className="text-[11px] text-muted-foreground max-w-[250px] text-center leading-snug">
                            To allow Nora to run secure diagnostic tests on your machine, download and run the appropriate daemon.
                        </p>
                        <div className="flex gap-4">
                            <a href="https://github.com/Abdulnasserh/Google_Hackathon/actions/runs/23094548351" target="_blank" rel="noopener noreferrer" className="text-xs text-sky-400 hover:text-sky-300 transition-colors bg-sky-500/10 px-3 py-1.5 rounded-md hover:bg-sky-500/20">
                                Windows (.exe)
                            </a>
                            <a href="https://github.com/Abdulnasserh/Google_Hackathon/actions/runs/23094548351" target="_blank" rel="noopener noreferrer" className="text-xs text-sky-400 hover:text-sky-300 transition-colors bg-sky-500/10 px-3 py-1.5 rounded-md hover:bg-sky-500/20">
                                macOS
                            </a>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
