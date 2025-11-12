import { useState } from 'react';
import { SessionsSidebar } from './components/Layout/SessionsSidebar';
import { ChatInterface } from './components/Chat/ChatInterface';
import { CodeWikiInterface } from './components/CodeWiki/CodeWikiInterface';
import { ApprovalDialog } from './components/ApprovalDialog';

type Tab = 'chat' | 'codewiki';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  return (
    <div className="h-screen flex bg-cream">
      {/* Left Sidebar - Sessions */}
      <SessionsSidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden bg-white">
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'codewiki' && <CodeWikiInterface />}
      </main>

      {/* Modals */}
      <ApprovalDialog />
    </div>
  );
}

export default App;
