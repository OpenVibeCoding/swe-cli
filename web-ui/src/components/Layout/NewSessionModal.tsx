import { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { FolderPlusIcon } from '@heroicons/react/24/outline';

interface NewSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => void;
  errorMessage?: string;
}

export function NewSessionModal({ isOpen, onClose, onCreate, errorMessage }: NewSessionModalProps) {
  const [workspaceName, setWorkspaceName] = useState('');

  const handleCreate = () => {
    if (workspaceName.trim()) {
      onCreate(workspaceName.trim());
      setWorkspaceName('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCreate();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Workspace">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Give your new workspace a name to help you identify it later.
        </p>
        <div>
          <label htmlFor="workspaceName" className="block text-sm font-medium text-gray-700 mb-2">
            Workspace Name
          </label>
          <div className="relative">
            <FolderPlusIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              id="workspaceName"
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g., my-react-app"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              autoFocus
            />
          </div>
        </div>
        {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
        <div className="flex justify-end gap-3 pt-4">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleCreate}>
            Create Workspace
          </Button>
        </div>
      </div>
    </Modal>
  );
}
