import React from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement>, React.RefAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
  error?: string;
  options: Array<{ value: string; label: string }>;
}

export function Select({ label, hint, error, id, options, required, ref, ...props }: SelectProps) {
  const selectId = id ?? label.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={selectId} className="text-sm font-medium text-secondary">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
      <select
        id={selectId}
        ref={ref}
        required={required}
        className={`border rounded px-3 py-2 text-sm bg-elevated text-primary focus:outline-none focus:ring-2 focus:ring-blue-500 ${error ? 'border-red-500' : 'border-line-strong'}`}
        {...props}
      >
        <option value="">— select —</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {hint && <p className="text-xs text-faint">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
Select.displayName = 'Select';
