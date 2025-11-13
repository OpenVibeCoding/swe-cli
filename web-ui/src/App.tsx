import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppNavBar } from './components/Layout/AppNavBar';
import { ChatPage } from './pages/ChatPage';
import { CodeWikiPage } from './pages/CodeWikiPage';
import { RepositoryDetailPage } from './components/CodeWiki/RepositoryDetailPage';

function App() {
  return (
    <Router>
      {/* Global Navigation Bar - appears on all pages */}
      <AppNavBar />

      {/* Main Content - with top padding for fixed navbar */}
      <div className="pt-14">
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/codewiki" element={<CodeWikiPage />} />
          <Route path="/codewiki/:repoName" element={<RepositoryDetailPage />} />
          <Route path="/" element={<Navigate to="/chat" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
