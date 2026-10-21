import { useEffect, useSyncExternalStore } from "react"
import type { PosProduct } from "../../lib/api"
import { addCustomerCartItem, clearCustomerCart, deleteCustomerCartItem, getCustomerCart, updateCustomerCartItem } from "../../lib/api"
import { useCustomerAuth } from "../auth/CustomerAuthContext"

export type MarketplaceCartItem = { product: PosProduct; qty: number; cartItemId: string }
let listeners: Array<() => void> = []
let snapshot: MarketplaceCartItem[] = []
if (typeof window !== "undefined") {
  window.localStorage.removeItem("dewa-jam-marketplace-cart")
  window.localStorage.removeItem("dewa-jam-marketplace-cart-owner")
}

function notify() { listeners.forEach((listener) => listener()) }
function updateCart(items: MarketplaceCartItem[]) { snapshot = items; notify() }
const subscribe = (listener: () => void) => { listeners = [...listeners, listener]; return () => { listeners = listeners.filter((item) => item !== listener) } }

export function useMarketplaceCart() {
  const { session } = useCustomerAuth()
  const items = useSyncExternalStore(subscribe, () => snapshot, () => [])
  const count = items.reduce((sum, item) => sum + item.qty, 0)
  function add(product: PosProduct, qty = 1) {
    if (!session) return
    void addCustomerCartItem(session.access_token, product.product_id, qty).then((remoteItem) => {
      const next = snapshot.filter((item) => item.product.product_id !== product.product_id)
      updateCart([...next, { product, qty: Math.min(remoteItem.qty, product.stok), cartItemId: remoteItem.cart_item_id }])
    }).catch(() => undefined)
  }
  function change(productId: string, qty: number) {
    if (!session) return
    const item = items.find((candidate) => candidate.product.product_id === productId)
    if (!item) return
    updateCart(items.map((candidate) => candidate.product.product_id === productId ? { ...candidate, qty } : candidate).filter((candidate) => candidate.qty > 0))
    if (qty > 0) void updateCustomerCartItem(session.access_token, item.cartItemId, productId, qty).catch(() => undefined)
    else void deleteCustomerCartItem(session.access_token, item.cartItemId).catch(() => undefined)
  }
  function remove(productId: string) {
    if (!session) return
    const item = items.find((candidate) => candidate.product.product_id === productId)
    updateCart(items.filter((candidate) => candidate.product.product_id !== productId))
    if (item) void deleteCustomerCartItem(session.access_token, item.cartItemId).catch(() => undefined)
  }
  function clear() { updateCart([]); if (session) void clearCustomerCart(session.access_token).catch(() => undefined) }
  useEffect(() => {
    if (!session) {
      updateCart([])
      return
    }
    void getCustomerCart(session.access_token).then((remote) => {
      updateCart(remote.items.filter((item) => item.qty > 0).map((item) => ({ product: item.product, qty: item.qty, cartItemId: item.cart_item_id })))
    }).catch(() => updateCart([]))
  }, [session])
  return { items, count, add, change, remove, clear }
}

export function marketplaceCartItems() { return snapshot }
