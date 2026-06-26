export default function Placeholder({ title, description, implementIn }: {
  title: string
  description: string
  implementIn?: string
}) {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="bg-card border border-border rounded-lg p-8 text-center text-muted-foreground">
        <p className="text-sm">{implementIn || 'Page will be implemented in the next phase.'}</p>
      </div>
    </div>
  )
}
