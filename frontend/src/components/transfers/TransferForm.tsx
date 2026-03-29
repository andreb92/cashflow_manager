import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { transfersApi } from '../../api/transfers';
import { paymentMethodsApi } from '../../api/paymentMethods';
import { assetsApi } from '../../api/assets';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Button } from '../ui/Button';
import type { Transfer } from '../../types/api';

type AccountType = Transfer['from_account_type'];
const ACCOUNT_TYPES: Array<{ value: string; label: string }> = [
  { value: 'bank', label: 'Bank account' },
  { value: 'saving', label: 'Saving account' },
  { value: 'investment', label: 'Investment account' },
  { value: 'pension', label: 'Pension fund' },
];

interface Fields {
  date: string; detail: string; amount: string;
  from_account_type: AccountType; from_account_name: string;
  to_account_type: AccountType; to_account_name: string;
  recurrence_months: string; notes: string;
}

interface Props { onSuccess: () => void; initial?: Transfer; }

export default function TransferForm({ onSuccess, initial }: Props) {
  const qc = useQueryClient();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { register, handleSubmit, watch, setValue } = useForm<Fields>({
    defaultValues: initial
      ? { ...initial, amount: String(initial.amount), recurrence_months: String(initial.recurrence_months ?? ''), notes: initial.notes ?? '' }
      : { date: format(new Date(), 'yyyy-MM-dd'), from_account_type: 'bank', to_account_type: 'saving' },
  });

  const currentYear = new Date().getFullYear();
  const { data: paymentMethods = [] } = useQuery({
    queryKey: ['payment-methods'],
    queryFn: () => paymentMethodsApi.list(true),
  });
  const { data: assets = [] } = useQuery({
    queryKey: ['assets', currentYear],
    queryFn: () => assetsApi.year(currentYear),
  });

  const fromType = watch('from_account_type');
  const toType = watch('to_account_type');
  const affectsBank = fromType === 'bank' || toType === 'bank';

  const fromMounted = useRef(false);
  const toMounted = useRef(false);
  useEffect(() => {
    if (!fromMounted.current) { fromMounted.current = true; return; }
    setValue('from_account_name', ''); // eslint-disable-line react-hooks/exhaustive-deps
  }, [fromType]);
  useEffect(() => {
    if (!toMounted.current) { toMounted.current = true; return; }
    setValue('to_account_name', ''); // eslint-disable-line react-hooks/exhaustive-deps
  }, [toType]);

  const accountNameOptions = (type: string): { value: string; label: string }[] => {
    if (type === 'bank') {
      const banks = paymentMethods.filter((m) => m.type === 'bank');
      if (banks.length === 0) return [{ value: '', label: '— no bank accounts —' }];
      return banks.map((b) => ({ value: b.name, label: b.name }));
    }
    const names = assets
      .filter((a) => a.asset_type === type)
      .map((a) => ({ value: a.asset_name, label: a.asset_name }));
    if (names.length === 0) return [{ value: '', label: `— no ${type} accounts —` }];
    return names;
  };

  const { mutate, isPending } = useMutation({
    mutationFn: (d: Fields) => {
      const body = {
        date: d.date, detail: d.detail, amount: parseFloat(d.amount),
        from_account_type: d.from_account_type, from_account_name: d.from_account_name,
        to_account_type: d.to_account_type, to_account_name: d.to_account_name,
        ...(d.recurrence_months ? { recurrence_months: parseInt(d.recurrence_months) } : {}),
        ...(d.notes ? { notes: d.notes } : {}),
      };
      return initial ? transfersApi.update(initial.id, body) : transfersApi.create(body);
    },
    onSuccess: () => {
      setSubmitError(null);
      qc.invalidateQueries({ queryKey: ['transfers'] });
      qc.invalidateQueries({ queryKey: ['summary'] });
      qc.invalidateQueries({ queryKey: ['assets'] });
      onSuccess();
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      setSubmitError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join('; ')
          : 'Failed to save. Please check your inputs and try again.'
      );
    },
  });

  return (
    <form onSubmit={handleSubmit((d) => mutate(d))} className="flex flex-col gap-3">
      <Input label="Date" type="date" required {...register('date', { required: true })} />
      <Input label="Detail" type="text" required {...register('detail', { required: true })} />
      <Input label="Amount (€)" type="number" step="0.01" required {...register('amount', { required: true })} />
      <p className={`text-xs ${affectsBank ? 'text-blue-600 dark:text-blue-400' : 'text-faint'}`}>
        {affectsBank
          ? 'This transfer will affect your bank balance.'
          : 'This transfer does not affect your bank balance.'}
      </p>
      <Select label="From account type" options={ACCOUNT_TYPES} {...register('from_account_type')} />
      <Select
        label="From account name"
        options={accountNameOptions(fromType)}
        required
        {...register('from_account_name', { required: true })}
      />
      <Select label="To account type" options={ACCOUNT_TYPES} {...register('to_account_type')} />
      <Select
        label="To account name"
        options={accountNameOptions(toType)}
        required
        {...register('to_account_name', { required: true })}
      />
      <Input label="Repeat for N months" type="number" min="1" {...register('recurrence_months')} />
      <Input label="Notes" type="text" {...register('notes')} />
      {submitError && (
        <p className="text-xs text-red-600 bg-red-50 dark:bg-red-900/20 rounded px-3 py-2">{submitError}</p>
      )}
      <Button type="submit" isLoading={isPending}>{initial ? 'Save' : 'Add transfer'}</Button>
    </form>
  );
}
