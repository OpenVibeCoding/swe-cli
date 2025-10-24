import { SessionsSidebar } from './components/Layout/SessionsSidebar';
import { ChatInterface } from './components/Chat/ChatInterface';
import { ApprovalDialog } from './components/ApprovalDialog';

function App() {
  return (
    <div className="h-screen flex bg-cream">
      {/* Left Sidebar - Sessions */}
      <SessionsSidebar />

      {/* Right Panel - Chat */}
      <main className="flex-1 flex flex-col overflow-hidden bg-white">
        <ChatInterface />
      </main>

      {/* Modals */}
      <ApprovalDialog />
    </div>
  );
}

export default App;
