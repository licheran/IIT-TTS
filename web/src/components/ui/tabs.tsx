import type { ComponentProps } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

/**
 * A tab that is a route. `solid` is the dark pill of the section bar (a link: it moves between
 * pages), `outline` the lighter one of a long list of tables (a tab, with `aria-selected`). Both are
 * 32 px high; the active one is filled.
 */
export function NavTab({
  className,
  look = 'outline',
  ...props
}: Omit<ComponentProps<typeof NavLink>, 'className'> & {
  className?: string
  look?: 'solid' | 'outline'
}) {
  return (
    <NavLink
      role={look === 'outline' ? 'tab' : undefined}
      className={({ isActive }) =>
        cn(
          'inline-flex h-control items-center rounded-control border px-3 text-sm',
          look === 'solid' && 'font-medium',
          isActive
            ? look === 'solid'
              ? 'border-neutral-900 bg-neutral-900 text-white'
              : 'border-blue-700 bg-blue-700 text-white'
            : look === 'solid'
              ? 'border-transparent text-neutral-700 hover:bg-neutral-100'
              : 'border-neutral-300 bg-white hover:bg-neutral-100',
          className,
        )
      }
      {...props}
    />
  )
}
