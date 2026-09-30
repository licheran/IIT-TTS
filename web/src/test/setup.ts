import '@testing-library/jest-dom/vitest'

// jsdom has no layout. Give elements a size so the virtual table renders rows, and stub
// ResizeObserver, which the virtualizer uses.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 1000 })
Element.prototype.scrollTo = () => {}
