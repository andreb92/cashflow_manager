import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { Transaction, PaymentMethod, Category } from '../../types/api';
import { fmt } from '../../utils/format';

interface Props {
  tx: Transaction;
  method?: PaymentMethod;
  category?: Category;
  onEdit: () => void;
  onDelete: () => void;
}

export default function TransactionRow({ tx, method, category, onEdit, onDelete }: Props) {
  const directionColor = tx.transaction_direction === 'income' ? 'green' : tx.transaction_direction === 'credit' ? 'blue' : 'red';
  return (
    <li className="flex items-center gap-3 py-2 border-b last:border-0 text-sm">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate text-primary">{tx.detail}</span>
          {tx.recurrence_months && (
            <span title="Recurring" className="text-blue-400 text-xs">↻</span>
          )}
          {tx.installment_total && tx.installment_index && (
            <Badge color="yellow">{tx.installment_index}/{tx.installment_total}</Badge>
          )}
        </div>
        <div className="text-muted text-xs mt-0.5">
          {tx.date}
          {tx.billing_month !== tx.date.slice(0, 7) + '-01' && (
            <span className="text-blue-500 ml-1" title="Credit card: billed in a different month">
              → billed {tx.billing_month.slice(0, 7)}
            </span>
          )}
          {' · '}{method?.name ?? tx.payment_method_id}
          {' · '}{category ? `${category.type}/${category.sub_type}` : ''}
        </div>
      </div>
      <Badge color={directionColor}>
        {tx.transaction_direction === 'income' ? '+' : '-'}€{fmt(tx.amount)}
      </Badge>
      <div className="flex gap-1">
        <Button variant="ghost" className="text-xs px-2" onClick={onEdit}>Edit</Button>
        <Button variant="ghost" className="text-xs px-2 text-red-500" onClick={onDelete}>Delete</Button>
      </div>
    </li>
  );
}
