import { Dialog } from 'radix-ui'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'

/**
 * A panel along the right edge that sits beside the page instead of over it (ADR-0009): nothing
 * behind it is blocked or dimmed, focus is not moved into it when it opens, and a click on the
 * page does not close it. Escape and the close button do.
 */
export function Drawer({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <Dialog.Root open modal={false} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Content
          aria-describedby={undefined}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
          onInteractOutside={(event) => event.preventDefault()}
          // Close after this key press has reached the field, which still sees the drawer open
          // and so leaves its own edit alone (Escape closes one layer at a time).
          onEscapeKeyDown={(event) => {
            event.preventDefault()
            window.setTimeout(onClose, 0)
          }}
          className="fixed right-0 top-0 z-40 flex h-full w-[30rem] max-w-full flex-col border-l border-neutral-300 bg-white shadow-xl"
        >
          <div className="flex items-center gap-2 border-b border-neutral-200 p-3">
            <Dialog.Title className="text-base font-semibold">{title}</Dialog.Title>
            <Dialog.Close asChild>
              <Button size="sm" variant="ghost" className="ml-auto" aria-label="Close lookup">
                ✕
              </Button>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
