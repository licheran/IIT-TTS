import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

/** A banner: a message set apart from the text around it. */
const noticeVariants = cva('rounded-control border p-3 text-sm', {
  variants: {
    tone: {
      info: 'border-blue-300 bg-blue-50',
      success: 'border-green-300 bg-green-50',
      error: 'border-red-300 bg-red-50',
    },
  },
  defaultVariants: { tone: 'info' },
})

export function Notice({
  className,
  tone,
  ...props
}: HTMLAttributes<HTMLDivElement> & VariantProps<typeof noticeVariants>) {
  return <div className={cn(noticeVariants({ tone }), className)} {...props} />
}

const badgeVariants = cva('rounded px-1 text-xs', {
  variants: {
    tone: {
      neutral: 'bg-neutral-100 text-neutral-800',
      success: 'bg-green-100 text-green-900',
      info: 'bg-blue-100 text-blue-900',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

/** A small label inside a line of text, such as "published". */
export function Badge({
  className,
  tone,
  ...props
}: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
