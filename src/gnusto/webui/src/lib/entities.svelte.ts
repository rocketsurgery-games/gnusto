import type { EntityInfo } from './types'

let sceneEntities = $state<Record<string, { name: string; image: string | null }>>({})
let entityBehaviors = $state<Record<string, string[]>>({})

export function updateEntities(entities: Record<string, { name: string; image: string | null }>) {
  sceneEntities = entities
}

export function updateBehaviors(entities: EntityInfo[]) {
  for (const e of entities) {
    entityBehaviors[e.id] = e.behaviors
  }
}

export function resolveEntityName(id: string): string {
  const entity = sceneEntities[id]
  if (entity) return entity.name
  // Fallback: strip @ and capitalize
  return id.replace(/^@/, '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function resolveEntityImage(id: string): string | null {
  return sceneEntities[id]?.image || null
}

export function resolveEntityBehaviors(id: string): string[] {
  return entityBehaviors[id] || []
}

export function speakerInitial(name: string): string {
  if (!name) return '?'
  const clean = name.replace(/^(the|a|an)\s+/i, '')
  return clean.charAt(0).toUpperCase()
}
