/**
 * Whether a behavior takes additional arguments.
 * Example: "ask-about <@topic>" → true, "examine" → false
 */
export function behaviorHasArgs(behavior: string): boolean {
  return /<[@\w]+>/.test(behavior)
}

/** Has exactly one entity arg (<@param>) and no other args. */
export function behaviorHasEntityArg(behavior: string): boolean {
  const entityArgs = behavior.match(/<@\w+>/g)
  const allArgs = behavior.match(/<[@\w]+>/g)
  return entityArgs?.length === 1 && allArgs?.length === 1
}

/** Has a value arg (<param> without @). */
export function behaviorHasValueArg(behavior: string): boolean {
  return /<(?!@)\w+>/.test(behavior)
}

/**
 * Convert a behavior string to a player command.
 * Strips parameter annotations and replaces hyphens with spaces.
 * Example: "ask-about <@topic>" + "brass key" → "ask about the brass key"
 */
export function behaviorToCommand(behavior: string, entityName: string): string {
  const verb = behavior.replace(/<[@\w]+>/g, '').trim().replace(/-/g, ' ')
  return `${verb} the ${entityName}`
}

/**
 * Build a command for a targeted two-entity action.
 *
 * Compound verb (ask-about <@topic>): "ask the hacker about the master key"
 *   → source entity goes between verb parts, target at end
 *
 * Simple verb (give <@item>): "give the carton to the hacker"
 *   → target after verb, source at end with "to"
 */
export function behaviorToTargetedCommand(
  behavior: string,
  sourceEntityName: string,
  targetEntityName: string,
): string {
  const verb = behavior.replace(/<[@\w]+>/g, '').trim()
  const parts = verb.split('-')

  if (parts.length > 1) {
    // Compound verb: "ask-about" → "ask the <source> about the <target>"
    return `${parts[0]} the ${sourceEntityName} ${parts.slice(1).join(' ')} the ${targetEntityName}`
  }
  // Simple verb: "give" → "give the <target> to the <source>"
  return `${parts[0]} the ${targetEntityName} to the ${sourceEntityName}`
}

/**
 * Convert a behavior string to a human-readable label.
 * Strips all parameter annotations and capitalizes.
 * Example: "ask-about <@topic>" → "Ask about"
 * Example: "type <value>" → "Type"
 */
export function behaviorLabel(behavior: string): string {
  const label = behavior.replace(/<[@\w]+>/g, '').trim().replace(/-/g, ' ')
  return label.charAt(0).toUpperCase() + label.slice(1)
}
