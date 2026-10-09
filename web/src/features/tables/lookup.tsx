import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { ReferenceDrawer } from './ReferenceDrawer'

/** What a field asks the lookup drawer to show and how to put a choice back. */
export interface LookupRequest {
  /** The drawer's title, for example "Building of [1LA] -GP". */
  title: string
  /** The sheets whose rows may be chosen (several: one tab each). */
  sheets: string[]
  /** A list cell takes several codes (a click adds or removes one). */
  multiple: boolean
  /** The field's text as it is now. */
  value: () => string
  /** Put a new text in the field. */
  change: (value: string) => void
  /** Give the keyboard back to the field. */
  refocus: () => void
}

interface Lookup {
  open: (request: LookupRequest) => void
  close: () => void
  /** True while the drawer is open: a field then keeps its edit when it loses focus. */
  isOpen: boolean
}

const Context = createContext<Lookup | null>(null)

/** The lookup of the table in view. Without a provider a field simply has no lookup. */
export function useLookup(): Lookup | null {
  return useContext(Context)
}

export function LookupProvider({
  datasetId,
  children,
}: {
  datasetId: number
  children: ReactNode
}) {
  const [request, setRequest] = useState<LookupRequest | null>(null)
  const close = useCallback(() => {
    setRequest((current) => {
      current?.refocus()
      return null
    })
  }, [])
  const value = useMemo<Lookup>(
    () => ({ open: setRequest, close, isOpen: request !== null }),
    [close, request],
  )
  return (
    <Context.Provider value={value}>
      {children}
      {request && <ReferenceDrawer datasetId={datasetId} request={request} onClose={close} />}
    </Context.Provider>
  )
}

const items = (value: string) =>
  value
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)

/** The text a click puts in a field: the code alone, or the list with the code added or removed. */
export function chosen(value: string, code: string, multiple: boolean): string {
  if (!multiple) return code
  const list = items(value)
  return (list.includes(code) ? list.filter((s) => s !== code) : [...list, code]).join(';')
}

export function isChosen(value: string, code: string, multiple: boolean): boolean {
  return multiple ? items(value).includes(code) : value.trim() === code
}
