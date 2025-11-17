import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  sessionName: string;
}

export function DeleteConfirmModal({ isOpen, onClose, onConfirm, sessionName }: DeleteConfirmModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Delete Workspace">
      <div className="space-y-4">
        <div className="flex items-start gap-4">
          <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
            <ExclamationTriangleIcon className="h-6 w-6 text-red-600" aria-hidden="true" />
          </div>
          <div className="mt-0 text-left">
            <p className="text-sm text-gray-600">
              Are you sure you want to delete the workspace{' '}
              <strong className="font-semibold text-gray-800">{sessionName}</strong>? This action is
              irreversible and all associated data will be lost.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-4">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm}>
            Delete Workspace
          </Button>
        </div>
      </div>
    </Modal>
  );
}
