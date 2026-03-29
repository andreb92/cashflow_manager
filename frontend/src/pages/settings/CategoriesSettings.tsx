import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { categoriesApi } from '../../api/categories';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import Modal from '../../components/ui/Modal';
import type { Category } from '../../types/api';

interface AddFields { type: string; sub_type: string; }
interface EditFields { type: string; sub_type: string; }

export default function CategoriesSettings() {
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [editCat, setEditCat] = useState<Category | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ['categories-all'],
    queryFn: () => categoriesApi.list(true),
  });

  const { register: registerAdd, handleSubmit: handleAdd, reset: resetAdd } = useForm<AddFields>();
  const { register: registerEdit, handleSubmit: handleEdit, reset: resetEdit } = useForm<EditFields>();

  const { mutate: create, isPending: creating } = useMutation({
    mutationFn: (d: AddFields) => categoriesApi.create(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories-all'] });
      qc.invalidateQueries({ queryKey: ['categories'] });
      setAddOpen(false);
      resetAdd();
    },
  });

  const { mutate: update, isPending: updating } = useMutation({
    mutationFn: (d: EditFields) => categoriesApi.update(editCat!.id, d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories-all'] });
      qc.invalidateQueries({ queryKey: ['categories'] });
      setEditCat(null);
    },
  });

  const { mutate: deactivate } = useMutation({
    mutationFn: (id: string) => categoriesApi.update(id, { is_active: false }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories-all'] });
      qc.invalidateQueries({ queryKey: ['categories'] });
    },
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-muted-bg rounded" />;

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button onClick={() => setAddOpen(true)}>+ Add category</Button>
      </div>
      <ul className="space-y-1">
        {categories.map((c) => (
          <li key={c.id} className="bg-surface border border-line rounded p-3 flex items-center justify-between text-sm text-primary">
            <div className="flex items-center gap-2">
              <span>{c.type}</span>
              <span className="text-faint">/</span>
              <span>{c.sub_type}</span>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" className="text-xs" onClick={() => { setEditCat(c); resetEdit({ type: c.type, sub_type: c.sub_type }); }}>Rename</Button>
              <Button variant="ghost" className="text-xs text-red-500" onClick={() => deactivate(c.id)}>Deactivate</Button>
            </div>
          </li>
        ))}
      </ul>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add category">
        <form onSubmit={handleAdd((d) => create(d))} className="flex flex-col gap-3">
          <Input label="Type" type="text" {...registerAdd('type', { required: true })} />
          <Input label="Sub-type" type="text" {...registerAdd('sub_type', { required: true })} />
          <Button type="submit" isLoading={creating}>Add</Button>
        </form>
      </Modal>

      <Modal open={!!editCat} onClose={() => setEditCat(null)} title="Rename category">
        <form onSubmit={handleEdit((d) => update(d))} className="flex flex-col gap-3">
          <Input label="Type" type="text" {...registerEdit('type', { required: true })} />
          <Input label="Sub-type" type="text" {...registerEdit('sub_type', { required: true })} />
          <p className="text-xs text-muted">Renaming updates the display name across all historical and future transactions immediately.</p>
          <Button type="submit" isLoading={updating}>Save</Button>
        </form>
      </Modal>
    </div>
  );
}
