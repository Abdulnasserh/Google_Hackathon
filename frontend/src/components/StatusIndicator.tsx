/**
 * StatusIndicator Component — Connection & Agent Status
 * =======================================================
 * Displays the current WebSocket connection status and
 * whether the agent is speaking/thinking.
 */

import { Wifi, WifiOff, Radio, AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/hooks/useWebSocket";

interface StatusIndicatorProps {
    status: ConnectionStatus;
    isAgentSpeaking: boolean;
}

const statusConfig: Record<
    ConnectionStatus,
    { label: string; icon: React.ReactNode; className: string; dot?: string }
> = {
    disconnected: {
        label: "Offline",
        icon: <WifiOff className="h-3 w-3" />,
        className: "border-neutral-600/40 text-neutral-400 bg-neutral-500/5",
    },
    connecting: {
        label: "Connecting",
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
        className: "border-amber-500/40 text-amber-400 bg-amber-500/5",
        dot: "bg-amber-400",
    },
    connected: {
        label: "Live",
        icon: <Wifi className="h-3 w-3" />,
        className: "border-emerald-500/40 text-emerald-400 bg-emerald-500/5",
        dot: "bg-emerald-400",
    },
    error: {
        label: "Error",
        icon: <AlertCircle className="h-3 w-3" />,
        className: "border-red-500/40 text-red-400 bg-red-500/5",
        dot: "bg-red-400",
    },
};

export function StatusIndicator({ status, isAgentSpeaking }: StatusIndicatorProps) {
    const config = statusConfig[status];

    return (
        <div className="flex items-center gap-2">
            <Badge
                variant="outline"
                className={cn(
                    "gap-1.5 py-1 px-2.5 text-xs font-medium transition-all duration-300",
                    config.className
                )}
            >
                {config.dot && (
                    <span
                        className={cn(
                            "h-1.5 w-1.5 rounded-full shrink-0",
                            config.dot,
                            status === "connected" && "animate-pulse"
                        )}
                    />
                )}
                {config.icon}
                {config.label}
            </Badge>

            {isAgentSpeaking && (
                <Badge
                    variant="outline"
                    className="gap-1.5 py-1 px-2.5 text-xs font-medium border-indigo-500/40 text-indigo-300 bg-indigo-500/5"
                >
                    <Radio className="h-3 w-3 animate-pulse" />
                    Speaking
                </Badge>
            )}
        </div>
    );
}
