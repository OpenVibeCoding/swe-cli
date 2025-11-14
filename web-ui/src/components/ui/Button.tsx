import React from 'react';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export type ButtonVariant = 'primary' | 'secondary' | 'subtle' | 'danger';
export type ButtonSize = 'xs' | 'sm' | 'md';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  loading?: boolean;
}

export function Button({
  className,
  variant = 'primary',
  size = 'sm',
  leftIcon,
  rightIcon,
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const base = 'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed';

  const sizes: Record<ButtonSize, string> = {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2.5 text-sm',
  };

  const variants: Record<ButtonVariant, string> = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700',
    secondary: 'bg-white text-gray-800 border border-gray-300 hover:bg-gray-50',
    subtle: 'bg-gray-50 text-gray-700 border border-gray-200 hover:bg-gray-100',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  return (
    <button
      className={cn(base, sizes[size], variants[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="mr-2 h-4 w-4 animate-spin border-2 border-white/60 border-t-transparent rounded-full" />
      )}
      {leftIcon && <span className={cn('mr-2 flex items-center', !children && 'mr-0')}>{leftIcon}</span>}
      {children}
      {rightIcon && <span className={cn('ml-2 flex items-center', !children && 'ml-0')}>{rightIcon}</span>}
    </button>
  );
}
