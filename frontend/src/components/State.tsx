export function LoadingState() { return <div className="loading-state" role="status" aria-label="Loading energy data"><span className="spinner" />Retrieving BMRS data and aligning forecast vintages…</div> }
export function ErrorState({ message }: { message: string }) { return <div className="error-state" role="alert"><strong>Data request could not complete.</strong><span>{message}</span></div> }
export function EmptyState({ title, detail }: { title: string; detail: string }) { return <div className="empty-state"><strong>{title}</strong><span>{detail}</span></div> }
