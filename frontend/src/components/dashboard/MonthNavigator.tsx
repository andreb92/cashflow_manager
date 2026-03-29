import { format, addMonths, subMonths } from 'date-fns';
import { Button } from '../ui/Button';

interface Props {
  current: Date;
  onChange: (d: Date) => void;
}

export default function MonthNavigator({ current, onChange }: Props) {
  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" onClick={() => onChange(subMonths(current, 1))}>‹</Button>
      <span className="font-medium text-secondary min-w-32 text-center">
        {format(current, 'MMMM yyyy')}
      </span>
      <Button variant="ghost" onClick={() => onChange(addMonths(current, 1))}>›</Button>
    </div>
  );
}
