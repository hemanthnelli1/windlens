export const mw = (value: number | null | undefined) => value === null || value === undefined ? '—' : `${Math.round(value).toLocaleString('en-GB')} MW`
export const signedMw = (value: number | null | undefined) => value === null || value === undefined ? '—' : `${value > 0 ? '+' : ''}${Math.round(value).toLocaleString('en-GB')} MW`
export const percent = (value: number | null | undefined) => value === null || value === undefined ? '—' : `${value.toFixed(1)}%`
export const dateTime = (value: string) => new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London', timeZoneName: 'short' }).format(new Date(value))
export const time = (value: string) => new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London' }).format(new Date(value))
