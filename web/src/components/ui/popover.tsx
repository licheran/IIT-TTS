import { Popover } from 'radix-ui'
import type { KeyboardEvent, ReactNode } from 'react'

/**
 * The panel of a cell editor that needs more room than the cell (a checklist, tags, JSON).
 * It hangs below the cell it belongs to, in a portal, so the table's scroll area cannot clip it,
 * and it moves to stay inside the window. The cell is the editor's nearest positioned ancestor.
 * Closing is the editor's job (Done, Cancel, Escape), so a click elsewhere does not close it.
 */
export function CellPopover({
  label,
  onKeyDown,
  children,
}: {
  label: string
  onKeyDown?: (event: KeyboardEvent) => void
  children: ReactNode
}) {
  return (
    <Popover.Root open>
      <Popover.Anchor asChild>
        <span aria-hidden className="pointer-events-none absolute inset-0" />
      </Popover.Anchor>
      <Popover.Portal>
        <Popover.Content
          role="dialog"
          aria-label={label}
          side="bottom"
          align="start"
          sideOffset={4}
          collisionPadding={8}
          className="z-50 w-72 rounded-control border border-neutral-300 bg-white p-2 text-sm shadow-lg"
          onKeyDown={onKeyDown}
          onInteractOutside={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
        >
          {children}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
