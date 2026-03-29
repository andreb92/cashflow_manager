import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { forecastsApi } from '../../api/forecasts';
import Modal from '../ui/Modal';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';

interface Props {
  open: boolean;
  onClose: () => void;
  forecastId: string;
  lineId: string;
}

interface Fields { valid_from: string; new_amount: string; }

export default function AdjustmentModal({ open, onClose, forecastId, lineId }: Props) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm<Fields>();

  const { mutate, isPending } = useMutation({
    mutationFn: (d: Fields) =>
      forecastsApi.addAdjustment(forecastId, lineId, {
        valid_from: `${d.valid_from}-01`,
        new_amount: parseFloat(d.new_amount),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['forecast-projection', forecastId] });
      qc.invalidateQueries({ queryKey: ['forecast', forecastId] });
      reset();
      onClose();
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Add adjustment">
      <form onSubmit={handleSubmit((d) => mutate(d))} className="flex flex-col gap-3">
        <Input label="Start month (YYYY-MM)" type="month" {...register('valid_from', { required: true })} />
        <Input label="New amount (€)" type="number" step="0.01" {...register('new_amount', { required: true })} />
        <Button type="submit" isLoading={isPending}>Add adjustment</Button>
      </form>
    </Modal>
  );
}
