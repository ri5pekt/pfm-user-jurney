export interface FunnelItem {
  id: string
  label: string
  type?: string
  count: number
  pct: number
  orders?: number
  convRate?: number
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
