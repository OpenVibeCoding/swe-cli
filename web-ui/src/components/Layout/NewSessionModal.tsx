import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { apiClient } from '../../api/client';

interface NewSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NewSessionModal({ isOpen, onClose }: NewSessionModalProps) {
  const [workspacePath, setWorkspacePath] = useState('');
  const [isPathValid, setIsPathValid] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [hasVerified, setHasVerified] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  if (!isOpen) return null;

  const handleVerify = async () => {
    if (!workspacePath.trim()) {
      return;
    }

    setIsVerifying(true);
    setHasVerified(false);
    try {
      const result = await apiClient.verifyPath(workspacePath);
      console.log('Verify path result:', result);
      console.log('Path:', workspacePath);
      console.log('Exists:', result.exists, 'Is Directory:', result.is_directory);

      if (result.exists && result.is_directory) {
        setIsPathValid(true);
      } else {
        setIsPathValid(false);
      }
    } catch (err) {
      console.error('Verify path error:', err);
      setIsPathValid(false);
    }
    setHasVerified(true);
    setIsVerifying(false);
  };

  const handleCreate = async () => {
    if (workspacePath.trim() && isPathValid) {
      console.log('Creating session with workspace:', workspacePath);
      setIsCreating(true);
      try {
        const result = await apiClient.createSession(workspacePath);
        console.log('Create session result:', result);
        window.location.reload();
      } catch (err) {
        console.error('Failed to create session:', err);
        setIsCreating(false);
      }
    }
  };

  const modalContent = (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      zIndex: 99999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '32px',
        borderRadius: '12px',
        minWidth: '500px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ margin: '0 0 24px 0', fontSize: '22px', fontWeight: '600' }}>New Workspace</h2>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
            Workspace Directory Path
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={workspacePath}
              onChange={(e) => {
                setWorkspacePath(e.target.value);
                setIsPathValid(false);
                setHasVerified(false);
              }}
              placeholder="/Users/username/projects/myapp"
              style={{
                flex: 1,
                padding: '10px 12px',
                fontSize: '14px',
                border: '2px solid #d1d5db',
                borderRadius: '8px',
                fontFamily: 'monospace',
                outline: 'none'
              }}
            />
            <button
              onClick={handleVerify}
              disabled={isVerifying || !workspacePath.trim()}
              style={{
                padding: '10px 16px',
                backgroundColor: (isVerifying || !workspacePath.trim()) ? '#9ca3af' : '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: (isVerifying || !workspacePath.trim()) ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                opacity: (isVerifying || !workspacePath.trim()) ? 0.7 : 1,
                transition: 'all 0.2s ease'
              }}
            >
              {isVerifying ? 'Verifying...' : 'Verify'}
            </button>
          </div>
          <p style={{
            marginTop: '6px',
            fontSize: '12px',
            color: hasVerified ? (isPathValid ? '#10b981' : '#ef4444') : '#6b7280'
          }}>
            {hasVerified
              ? (isPathValid ? '✓ Valid directory' : '✗ Invalid directory')
              : 'Enter the absolute path to your project directory'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '10px 20px',
              border: '1px solid #d1d5db',
              backgroundColor: 'white',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!isPathValid || isCreating}
            style={{
              flex: 1,
              padding: '10px 20px',
              backgroundColor: (isPathValid && !isCreating) ? '#3b82f6' : '#9ca3af',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: (isPathValid && !isCreating) ? 'pointer' : 'not-allowed',
              fontSize: '14px',
              fontWeight: '500',
              opacity: isCreating ? 0.7 : 1
            }}
          >
            {isCreating ? 'Creating...' : 'Create Workspace'}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
