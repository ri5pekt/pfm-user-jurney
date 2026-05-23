const flagModules = import.meta.glob(
  '../assets/images/flags/*.png',
  { eager: true, import: 'default' },
) as Record<string, string>

export function flagUrl(country: string | null | undefined): string | undefined {
  if (!country) return undefined
  return flagModules[`../assets/images/flags/${country}.png`]
}
