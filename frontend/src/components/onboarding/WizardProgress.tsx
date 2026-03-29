interface Props {
  current: number;
  total: number;
}

export default function WizardProgress({ current, total }: Props) {
  return (
    <div className="mb-6">
      <p className="text-sm text-gray-500 mb-2">Step {current} of {total}</p>
      <ol className="flex gap-1">
        {Array.from({ length: total }, (_, i) => {
          const n = i + 1;
          const done = n < current;
          const active = n === current;
          return (
            <li
              key={n}
              role="listitem"
              className={`h-2 flex-1 rounded-full ${done ? 'bg-blue-600' : active ? 'bg-blue-200' : 'bg-gray-200'}`}
            />
          );
        })}
      </ol>
    </div>
  );
}
