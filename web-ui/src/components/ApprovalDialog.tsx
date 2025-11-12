import { useEffect } from 'react';
import { useChatStore } from '../stores/chat';

export function ApprovalDialog() {
  const pendingApproval = useChatStore(state => state.pendingApproval);
  const respondToApproval = useChatStore(state => state.respondToApproval);

  // Debug log
  useEffect(() => {
    if (pendingApproval) {
      console.log('[ApprovalDialog] Showing approval dialog:', pendingApproval);
    } else {
      console.log('[ApprovalDialog] No pending approval');
    }
  }, [pendingApproval]);

  if (!pendingApproval) {
    return null;
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === '1') {
        handleApprove();
      } else if (e.key === '2') {
        handleApproveAll();
      } else if (e.key === '3') {
        handleDeny();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [pendingApproval]);

  const handleApprove = () => {
    respondToApproval(pendingApproval.id, true, false);
  };

  const handleApproveAll = () => {
    respondToApproval(pendingApproval.id, true, true);
  };

  const handleDeny = () => {
    respondToApproval(pendingApproval.id, false, false);
  };

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white rounded-xl shadow-2xl border border-gray-200 max-w-2xl w-full mx-4 animate-slide-up">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Approval Required</h2>
          <p className="text-sm text-gray-600 mt-1">
            The assistant needs permission to execute the following operation
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-4">
          {/* Tool Name */}
          <div>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
              Tool
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary-500" />
              <code className="text-sm font-mono bg-gray-50 px-2 py-1 rounded border border-gray-200">
                {pendingApproval.tool_name}
              </code>
            </div>
          </div>

          {/* Description */}
          <div>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
              Description
            </div>
            <p className="text-sm text-gray-900 leading-relaxed">
              {pendingApproval.description}
            </p>
          </div>

          {/* Preview */}
          {pendingApproval.preview && (
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                Preview
              </div>
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 max-h-48 overflow-y-auto">
                <pre className="text-xs text-gray-900 font-mono whitespace-pre-wrap">
                  {pendingApproval.preview}
                </pre>
              </div>
            </div>
          )}

          {/* Arguments */}
          {Object.keys(pendingApproval.arguments).length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                Arguments
              </div>
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 max-h-64 overflow-y-auto">
                <pre className="text-xs text-gray-900 font-mono whitespace-pre-wrap">
                  {JSON.stringify(pendingApproval.arguments, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Warning */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex gap-3">
              <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-amber-900">Review carefully before approving</p>
                <p className="text-xs text-amber-700 mt-1">
                  This operation will be executed with your current permissions. Make sure you understand what it will do.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer - 3 Options */}
        <div className="border-t border-gray-200 px-6 py-5 bg-gray-50">
          <div className="space-y-2">
            {/* Option 1: Yes, run this command */}
            <button
              onClick={handleApprove}
              className="w-full px-4 py-3 text-sm font-medium text-left bg-white border-2 border-green-300 rounded-lg hover:bg-green-50 hover:border-green-400 transition-all flex items-center gap-3 group"
            >
              <div className="w-6 h-6 rounded-full bg-green-100 group-hover:bg-green-200 flex items-center justify-center text-green-700 font-semibold text-xs">
                1
              </div>
              <span className="text-gray-900">Yes, run this command</span>
            </button>

            {/* Option 2: Yes, and auto-approve */}
            <button
              onClick={handleApproveAll}
              className="w-full px-4 py-3 text-sm font-medium text-left bg-white border-2 border-blue-300 rounded-lg hover:bg-blue-50 hover:border-blue-400 transition-all flex items-center gap-3 group"
            >
              <div className="w-6 h-6 rounded-full bg-blue-100 group-hover:bg-blue-200 flex items-center justify-center text-blue-700 font-semibold text-xs">
                2
              </div>
              <div className="flex-1">
                <div className="text-gray-900">Yes, and auto-approve all <span className="font-semibold text-blue-700">{pendingApproval.tool_name}</span> commands</div>
                <div className="text-xs text-gray-500 mt-0.5">Future similar commands will run automatically</div>
              </div>
            </button>

            {/* Option 3: No, cancel */}
            <button
              onClick={handleDeny}
              className="w-full px-4 py-3 text-sm font-medium text-left bg-white border-2 border-red-300 rounded-lg hover:bg-red-50 hover:border-red-400 transition-all flex items-center gap-3 group"
            >
              <div className="w-6 h-6 rounded-full bg-red-100 group-hover:bg-red-200 flex items-center justify-center text-red-700 font-semibold text-xs">
                3
              </div>
              <span className="text-gray-900">No, cancel and provide feedback</span>
            </button>
          </div>

          {/* Keyboard shortcuts hint */}
          <div className="mt-4 pt-3 border-t border-gray-200 text-center">
            <p className="text-xs text-gray-500">
              Press <kbd className="px-1.5 py-0.5 bg-gray-200 border border-gray-300 rounded text-xs font-mono">1</kbd>, <kbd className="px-1.5 py-0.5 bg-gray-200 border border-gray-300 rounded text-xs font-mono">2</kbd>, or <kbd className="px-1.5 py-0.5 bg-gray-200 border border-gray-300 rounded text-xs font-mono">3</kbd> to select
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
