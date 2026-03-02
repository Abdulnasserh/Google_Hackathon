/**
 * App Component — Root Application Shell
 * ========================================
 * The root component for the AI PC Live Technician frontend.
 * Sets up the dark theme and renders the ChatInterface.
 *
 * Architecture:
 *   App (dark theme wrapper)
 *     └── ChatInterface
 *           ├── Header (logo, status, connect button)
 *           ├── Messages Area (ScrollArea + MessageBubbles)
 *           └── Input Area (VoiceButton / TextInput)
 */

import { ChatInterface } from "@/components/ChatInterface";

function App() {
  return (
    <div className="dark">
      <ChatInterface />
    </div>
  );
}

export default App;
