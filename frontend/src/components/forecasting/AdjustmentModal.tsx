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

interface Fields {
  valid_from: string;
  new_amount: string;
  adjustment_type: 'fixed' | 'percentage';
}

export default function AdjustmentModal({ open, onClose, forecastId, lineId }: Props) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset, watch } = useForm<Fields>({
    defaultValues: { adjustment_type: 'fixed' },
  });
  const adjustmentType = watch('adjustment_type');

  const { mutate, isPending } = useMutation({
    mutationFn: (d: Fields) =>
      forecastsApi.addAdjustment(forecastId, lineId, {
        valid_from: `${d.valid_from}-01`,
        new_amount: parseFloat(d.new_amount),
        adjustment_type: d.adjustment_type,
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
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-secondary">Adjustment type</label>
          <select
            {...register('adjustment_type')}
            className="border border-line-strong rounded px-3 py-2 text-sm bg-elevated text-primary"
          >
            <option value="fixed">Fixed amount (€)</option>
            <option value="percentage">Percentage change (%)</option>
          </select>
        </div>
        <Input
          label={adjustmentType === 'percentage' ? 'Percentage change (e.g. 5 for +5%, -10 for -10%)' : 'New amount (€)'}
          type="number"
          step={adjustmentType === 'percentage' ? '0.1' : '0.01'}
          {...register('new_amount', { required: true })}
        />
        <Button type="submit" isLoading={isPending}>Add adjustment</Button>
      </form>
    </Modal>
  );
}
