import { Header } from './components/Layout/Header';
import { ChatInterface } from './components/Chat/ChatInterface';
import { ApprovalDialog } from './components/ApprovalDialog';

function App() {
  return (
    <div className="h-screen flex flex-col bg-surface">
      <Header />
      <main className="flex-1 overflow-hidden bg-surface">
        <ChatInterface />
      </main>
      <ApprovalDialog />
    </div>
  );
}

export default App;
