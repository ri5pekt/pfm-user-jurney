export interface BreakdownItem {
  label:     string
  key?:      string       // raw DB value (e.g. 'email', 'paid_social') — used for session filtering
  count:     number
  orders:    number
  revenue:   number
  pct:       number       // % of parent sessions
  convRate?: number       // orders / count * 100 — present on channel items
  breakdown?: BreakdownItem[]  // campaigns nested under a channel item
}

export interface FunnelItem {
  id: string
  label: string
  type?: string
  count: number
  pct: number
  orders?: number
  convRate?: number
  revenue?: number
  breakdown?: BreakdownItem[]
}

export interface SimpleNode {
  count: number
  pct: number
}

export interface CountryItem {
  country: string
  count:   number
  pct:     number
}

export interface FunnelData {
  total:             number
  totalRevenue:      number
  aov:               number
  trackedOrders:     number
  countries:         CountryItem[]
  sources:           FunnelItem[]
  landingPages:      FunnelItem[]
  pages:             FunnelItem[]
  productPages:      FunnelItem[]
  postPurchasePages: FunnelItem[]
  cart:              SimpleNode
  checkout:          SimpleNode
  thankyou:          SimpleNode
}
