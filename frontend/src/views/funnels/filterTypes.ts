export type FilterField    = 'country' | 'channel' | 'source' | 'entry_url' | 'referrer'
export type FilterOperator = 'is_any' | 'contains' | 'equals' | 'starts_with' | 'is_set' | 'is_not_set'

export interface ActiveFilter {
  id:       number
  field:    FilterField
  operator: FilterOperator
  values:   string[]
  label:    string      // human-readable summary, e.g. "Country is US, GB"
}

export interface FilterDef {
  field:   FilterField
  label:   string
  group:   string
  type:    'multi_select' | 'string' | 'presence'
}

export const FILTER_DEFS: FilterDef[] = [
  { field: 'country',   label: 'Country',     group: 'Session',  type: 'multi_select' },
  { field: 'channel',   label: 'Channel',     group: 'Session',  type: 'multi_select' },
  { field: 'source',    label: 'Source',      group: 'Session',  type: 'multi_select' },
  { field: 'entry_url', label: 'Entry page',  group: 'Path',     type: 'string'       },
  { field: 'referrer',  label: 'Referrer URL',group: 'Path',     type: 'string'       },
]

let _id = 0
export function nextFilterId() { return ++_id }

export function buildFilterLabel(field: FilterField, operator: FilterOperator, values: string[]): string {
  const def = FILTER_DEFS.find(d => d.field === field)
  const name = def?.label ?? field
  if (operator === 'is_any')      return `${name} is ${values.join(', ')}`
  if (operator === 'contains')    return `${name} contains "${values[0]}"`
  if (operator === 'equals')      return `${name} = "${values[0]}"`
  if (operator === 'starts_with') return `${name} starts with "${values[0]}"`
  if (operator === 'is_set')      return `${name} is set`
  if (operator === 'is_not_set')  return `${name} is not set`
  return name
}
