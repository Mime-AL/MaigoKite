export interface PositionedNode {
  node: { id: string; turnId: string }
  position: number
}
export function inkBuckets(nodes: PositionedNode[], resolution = 80) {
  const slots = new Map<number, { node: PositionedNode['node']; count: number }>()
  for (const item of nodes) {
    const slot = Math.min(resolution - 1, Math.max(0, Math.floor(item.position * resolution)))
    const bucket = slots.get(slot)
    if (bucket) bucket.count++
    else slots.set(slot, { node: item.node, count: 1 })
  }
  return [...slots]
    .sort(([a], [b]) => a - b)
    .map(([slot, bucket]) => ({
      slot,
      node: bucket.node,
      density: Math.min(1, bucket.count / 5),
      top: (slot * 100) / resolution,
    }))
}
