import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { forecastsApi } from '../../api/forecasts';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';

interface Fields { name: string; base_year: string; projection_years: string; }
interface Props { onSuccess: () => void; }

export default function CreateForecastForm({ onSuccess }: Props) {
  const qc = useQueryClient();
  const { register, handleSubmit } = useForm<Fields>({
    defaultValues: { base_year: String(new Date().getFullYear()), projection_years: '3' },
  });

  const { mutate, isPending } = useMutation({
    mutationFn: (d: Fields) =>
      forecastsApi.create({
        name: d.name,
        base_year: parseInt(d.base_year),
        projection_years: parseInt(d.projection_years),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['forecasts'] });
      onSuccess();
    },
  });

  return (
    <form onSubmit={handleSubmit((d) => mutate(d))} className="flex flex-col gap-3">
      <Input label="Forecast name" type="text" {...register('name', { required: true })} />
      <Input label="Base year" type="number" min="2000" max="2100" {...register('base_year', { required: true })} />
      <Input label="Projection years (1–10)" type="number" min="1" max="10" {...register('projection_years', { required: true })} />
      <p className="text-xs text-gray-500">
        Recurring transactions from the base year will be automatically imported as forecast lines.
      </p>
      <Button type="submit" isLoading={isPending}>Create forecast</Button>
    </form>
  );
}
