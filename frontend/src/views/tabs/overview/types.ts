export interface FunnelItem {
  id: string
  label: string
  type?: string
  count: number
  pct: number
}

export interface SimpleNode {
  count: number
  pct: number
}

export interface FunnelData {
  total:             number
  sources:           FunnelItem[]
  landingPages:      FunnelItem[]
  pages:             FunnelItem[]
  productPages:      FunnelItem[]
  postPurchasePages: FunnelItem[]
  cart:              SimpleNode
  checkout:          SimpleNode
  thankyou:          SimpleNode
}
