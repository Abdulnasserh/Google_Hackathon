/**
 * VoiceButton Component — Animated Microphone Button
 * ====================================================
 * Toggles voice recording with pulse-ring animations and wave bars.
 */

import { Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";

interface VoiceButtonProps {
    isRecording: boolean;
    isDisabled: boolean;
    onToggle: () => void;
}

export function VoiceButton({ isRecording, isDisabled, onToggle }: VoiceButtonProps) {
    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <div className="relative flex items-center justify-center">
                    {/* Pulse rings when recording */}
                    {isRecording && (
                        <>
                            <span className="absolute inset-0 rounded-full bg-red-500/25 animate-pulse-ring" />
                            <span
                                className="absolute inset-0 rounded-full bg-red-500/15 animate-pulse-ring"
                                style={{ animationDelay: "0.6s" }}
                            />
                        </>
                    )}

                    <Button
                        variant={isRecording ? "destructive" : "default"}
                        size="icon"
                        onClick={onToggle}
                        disabled={isDisabled}
                        aria-label={isRecording ? "Stop recording" : "Start voice input"}
                        className={cn(
                            "relative z-10 h-13 w-13 rounded-full transition-all duration-300",
                            isRecording
                                ? "bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/35 scale-110"
                                : "bg-gradient-to-br from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 shadow-lg shadow-sky-500/30 hover:shadow-sky-500/50 hover:scale-105"
                        )}
                    >
                        {isRecording
                            ? <MicOff className="h-5 w-5 text-white" />
                            : <Mic className="h-5 w-5 text-white" />
                        }
                    </Button>
                </div>
            </TooltipTrigger>
            <TooltipContent>
                {isRecording ? "Stop recording" : "Start voice input"}
            </TooltipContent>
        </Tooltip>
    );
}

/**
 * VoiceWaveIndicator — Animated bars shown while recording
 */
export function VoiceWaveIndicator({ isActive }: { isActive: boolean }) {
    if (!isActive) return null;
    return (
        <div className="flex items-center gap-[3px] h-6" aria-hidden>
            {[...Array(5)].map((_, i) => (
                <span
                    key={i}
                    className="voice-wave-bar w-[3px] rounded-full bg-gradient-to-t from-sky-400 to-indigo-500"
                    style={{ minHeight: "4px" }}
                />
            ))}
        </div>
    );
}
