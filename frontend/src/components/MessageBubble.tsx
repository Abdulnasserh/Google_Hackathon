/**
 * MessageBubble Component — Chat Message Display
 * =================================================
 * Renders individual chat messages with distinct styling for user vs AI.
 * Supports partial (streaming) messages with shimmer effect.
 * Supports image attachments and copy-to-clipboard.
 */

import { useState, useCallback } from "react";
import { Bot, User, Image as ImageIcon, X, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import type { Message } from "@/hooks/useWebSocket";

interface MessageBubbleProps {
    message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === "user";
    const [isImageExpanded, setIsImageExpanded] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = useCallback(async () => {
        try {
            await navigator.clipboard.writeText(message.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            /* silent */
        }
    }, [message.content]);

    return (
        <>
            <div
                className={cn(
                    "group flex gap-3 animate-fade-in-up",
                    isUser ? "flex-row-reverse" : "flex-row"
                )}
            >
                {/* Avatar */}
                <Avatar
                    className={cn(
                        "h-8 w-8 shrink-0 ring-2 ring-offset-2 ring-offset-background",
                        isUser ? "ring-sky-500/50" : "ring-indigo-500/50"
                    )}
                >
                    <AvatarFallback
                        className={cn(
                            "text-xs font-bold",
                            isUser
                                ? "bg-gradient-to-br from-sky-500 to-cyan-400 text-white"
                                : "bg-gradient-to-br from-indigo-500 to-violet-500 text-white"
                        )}
                    >
                        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </AvatarFallback>
                </Avatar>

                {/* Bubble + copy button wrapper */}
                <div className={cn("flex items-end gap-1.5 max-w-[78%]", isUser ? "flex-row-reverse" : "flex-row")}>
                    {/* Message Bubble */}
                    <div
                        className={cn(
                            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                            isUser
                                ? "bg-gradient-to-br from-sky-500 to-indigo-600 text-white rounded-tr-sm"
                                : "glass-card text-foreground rounded-tl-sm",
                            message.isPartial && "shimmer"
                        )}
                    >
                        {/* Image Attachment */}
                        {message.imageUrl && (
                            <div className="mb-2 -mx-1 -mt-0.5">
                                <button
                                    onClick={() => setIsImageExpanded(true)}
                                    className="relative group/img cursor-pointer rounded-lg overflow-hidden block"
                                >
                                    <img
                                        src={message.imageUrl}
                                        alt="Attached image"
                                        className="max-h-48 w-auto rounded-lg object-cover transition-transform duration-200 group-hover/img:scale-[1.02]"
                                    />
                                    <div className="absolute inset-0 bg-black/0 group-hover/img:bg-black/20 transition-colors rounded-lg flex items-center justify-center">
                                        <ImageIcon className="h-6 w-6 text-white opacity-0 group-hover/img:opacity-100 transition-opacity drop-shadow-lg" />
                                    </div>
                                </button>
                            </div>
                        )}

                        {/* Content — detect inline code blocks */}
                        <MessageContent content={message.content} isUser={isUser} />

                        {/* Timestamp row */}
                        <div
                            className={cn(
                                "text-[10px] mt-1.5 opacity-50 flex items-center gap-1",
                                isUser ? "justify-end" : "justify-start"
                            )}
                        >
                            <span>
                                {message.timestamp.toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                })}
                            </span>
                            {message.isTranscription && <span>🎤</span>}
                            {message.imageUrl && <span>📷</span>}
                        </div>
                    </div>

                    {/* Copy button — visible on hover */}
                    {message.content && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleCopy}
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-muted-foreground hover:text-foreground shrink-0 mb-0.5"
                            aria-label="Copy message"
                        >
                            {copied
                                ? <Check className="h-3.5 w-3.5 text-emerald-400" />
                                : <Copy className="h-3.5 w-3.5" />
                            }
                        </Button>
                    )}
                </div>
            </div>

            {/* Fullscreen Image Lightbox */}
            {isImageExpanded && message.imageUrl && (
                <div
                    className="fixed inset-0 z-[100] bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in-up"
                    onClick={() => setIsImageExpanded(false)}
                >
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsImageExpanded(false)}
                        className="absolute top-4 right-4 h-10 w-10 rounded-full bg-white/10 hover:bg-white/20 text-white"
                    >
                        <X className="h-5 w-5" />
                    </Button>
                    <img
                        src={message.imageUrl}
                        alt="Expanded image"
                        className="max-w-[90vw] max-h-[85vh] object-contain rounded-xl shadow-2xl"
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
            )}
        </>
    );
}

// ---------------------------------------------------------------------------
// MessageContent — renders plain text with inline code highlighting
// ---------------------------------------------------------------------------
function MessageContent({ content, isUser }: { content: string; isUser: boolean }) {
    // Split on ```code blocks``` or `inline code`
    const parts = content.split(/(```[\s\S]*?```|`[^`]+`)/g);

    return (
        <div className="space-y-1.5">
            {parts.map((part, i) => {
                if (part.startsWith("```") && part.endsWith("```")) {
                    const code = part.slice(3, -3).replace(/^\w+\n/, ""); // strip lang hint
                    return (
                        <pre
                            key={i}
                            className={cn(
                                "text-xs rounded-lg p-3 overflow-x-auto font-mono leading-relaxed",
                                isUser
                                    ? "bg-white/10 text-sky-100"
                                    : "bg-black/30 text-emerald-300 border border-white/5"
                            )}
                        >
                            <code>{code.trim()}</code>
                        </pre>
                    );
                }
                if (part.startsWith("`") && part.endsWith("`")) {
                    const code = part.slice(1, -1);
                    return (
                        <code
                            key={i}
                            className={cn(
                                "text-xs font-mono px-1.5 py-0.5 rounded",
                                isUser
                                    ? "bg-white/15 text-sky-100"
                                    : "bg-black/25 text-emerald-300"
                            )}
                        >
                            {code}
                        </code>
                    );
                }
                return (
                    <p key={i} className="whitespace-pre-wrap break-words">
                        {part}
                    </p>
                );
            })}
        </div>
    );
}

// ---------------------------------------------------------------------------
// ThinkingIndicator — shows when the agent is processing
// ---------------------------------------------------------------------------
export function ThinkingIndicator() {
    return (
        <div className="flex gap-3 animate-fade-in-up">
            <Avatar className="h-8 w-8 shrink-0 ring-2 ring-indigo-500/50 ring-offset-2 ring-offset-background">
                <AvatarFallback className="bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
                    <Bot className="h-4 w-4" />
                </AvatarFallback>
            </Avatar>
            <div className="glass-card rounded-2xl rounded-tl-sm px-5 py-3.5 flex items-center gap-1.5">
                {[...Array(3)].map((_, i) => (
                    <span key={i} className="thinking-dot h-2 w-2 rounded-full bg-indigo-400" />
                ))}
            </div>
        </div>
    );
}
