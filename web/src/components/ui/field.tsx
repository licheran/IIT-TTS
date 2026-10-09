import { cva, type VariantProps } from 'class-variance-authority'
import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from 'react'
import { cn } from '@/lib/utils'

/** One look for text-like inputs and selects, at the two control heights. */
export const fieldVariants = cva(
  'rounded-control border border-neutral-300 bg-white px-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: { size: { sm: 'h-control-sm', md: 'h-control' } },
    defaultVariants: { size: 'md' },
  },
)

type FieldProps = VariantProps<typeof fieldVariants>

export function Input({
  className,
  size,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> & FieldProps) {
  return <input className={cn(fieldVariants({ size }), className)} {...props} />
}

export function Select({
  className,
  size,
  ...props
}: Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> & FieldProps) {
  return <select className={cn(fieldVariants({ size }), className)} {...props} />
}

/** A bare checkbox (in a table cell, where the label is an `aria-label`). */
export function Checkbox({
  className,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'>) {
  return <input type="checkbox" className={cn('h-4 w-4', className)} {...props} />
}

/** A file picker. */
export const FileInput = forwardRef<
  HTMLInputElement,
  Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>
>(function FileInput({ className, ...props }, ref) {
  return <input ref={ref} type="file" className={cn('text-sm', className)} {...props} />
})

/** A checkbox with its text, in one line. */
export function Check({
  children,
  className,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'> & { children: ReactNode }) {
  return (
    <label className={cn('flex h-control items-center gap-2 text-sm', className)}>
      <Checkbox {...props} />
      {children}
    </label>
  )
}

/** A label above its control. */
export function Field({
  label,
  className,
  children,
}: {
  label: ReactNode
  className?: string
  children: ReactNode
}) {
  return (
    <label className={cn('flex flex-col gap-1 text-sm', className)}>
      {label}
      {children}
    </label>
  )
}
