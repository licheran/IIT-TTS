import { cva, type VariantProps } from 'class-variance-authority'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const variants = cva(
  'inline-flex items-center justify-center gap-1 rounded-md border text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'border-blue-700 bg-blue-700 text-white hover:bg-blue-800',
        secondary: 'border-neutral-300 bg-white text-neutral-900 hover:bg-neutral-100',
        danger: 'border-red-300 bg-white text-red-700 hover:bg-red-50',
        ghost: 'border-transparent bg-transparent text-neutral-700 hover:bg-neutral-100',
      },
      size: { sm: 'h-7 px-2', md: 'h-9 px-3' },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants>

export function Button({ className, variant, size, type = 'button', ...props }: ButtonProps) {
  return <button type={type} className={cn(variants({ variant, size }), className)} {...props} />
}
