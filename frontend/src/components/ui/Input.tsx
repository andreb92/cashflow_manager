import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement>, React.RefAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

export function Input({ label, hint, error, id, className = '', required, ref, ...props }: InputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-medium text-secondary">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        id={inputId}
        ref={ref}
        required={required}
        className={`border rounded-md px-3 py-2 text-sm bg-elevated text-primary placeholder-faint focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          error ? 'border-red-500' : 'border-line-strong'
        } ${className}`}
        {...props}
      />
      {hint && <p className="text-xs text-faint">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
Input.displayName = 'Input';
