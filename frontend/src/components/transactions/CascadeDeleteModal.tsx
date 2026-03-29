import Modal from '../ui/Modal';
import { Button } from '../ui/Button';

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (cascade: 'single' | 'future' | 'all') => void;
  isRecurring: boolean;
  isPending: boolean;
}

export default function CascadeDeleteModal({ open, onClose, onConfirm, isRecurring, isPending }: Props) {
  return (
    <Modal open={open} onClose={onClose} title="Delete transaction">
      {isRecurring ? (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-gray-600">This is a recurring transaction. What do you want to delete?</p>
          <Button variant="secondary" onClick={() => onConfirm('single')} isLoading={isPending}>This one only</Button>
          <Button variant="secondary" onClick={() => onConfirm('future')} isLoading={isPending}>This and all future</Button>
          <Button onClick={() => onConfirm('all')} isLoading={isPending}>All in series</Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-gray-600">Delete this transaction?</p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button onClick={() => onConfirm('single')} isLoading={isPending}>Delete</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
