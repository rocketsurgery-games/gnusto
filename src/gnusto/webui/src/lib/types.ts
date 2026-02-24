// Content block types (matching Python render.py)

export interface EntityInfo {
  id: string
  name: string
}

export interface ExitDetail {
  direction: string
  destination: string
}

export interface RoomEnterBlock {
  type: 'room_enter'
  room_id: string
  name: string
  description: string
  exits: ExitDetail[]
  objects: EntityInfo[]
  inventory: EntityInfo[]
  image: string | null
}

export interface ActionResultBlock {
  type: 'action_result'
  text: string
}

export interface NarrateBlock {
  type: 'narrate'
  text: string
}

export interface SpeakBlock {
  type: 'speak'
  text: string
  speaker: string | null
  manner: string | null
}

export interface ThinkBlock {
  type: 'think'
  text: string
}

export interface AmbientBlock {
  type: 'ambient'
  text: string
}

export interface RevealBlock {
  type: 'reveal'
  text: string
  entity: string | null
}

export interface FocusBlock {
  type: 'focus'
  text: string
  entity: string | null
}

export interface ImageBlock {
  type: 'image'
  src: string
  alt: string
  layout: 'inline' | 'float-left' | 'float-right' | 'background'
  size: 'small' | 'medium' | 'large' | 'full'
}

export interface SystemMessageBlock {
  type: 'system'
  text: string
  level: 'info' | 'warning' | 'error'
}

export interface CommandBlock {
  type: 'command'
  text: string
}

export interface DebugBlock {
  type: 'debug'
  label: string
  content: string
}

export type ContentBlock = RoomEnterBlock | ActionResultBlock | NarrateBlock | SpeakBlock
  | ThinkBlock | AmbientBlock | RevealBlock | FocusBlock
  | ImageBlock | SystemMessageBlock | CommandBlock | DebugBlock

// Renderable block: a ContentBlock with optional layout metadata stamped at insert time
export type RenderableBlock = ContentBlock & {
  _side?: 'image-left' | 'image-right'
}

// Server messages
export interface BlocksMessage {
  type: 'blocks'
  blocks: ContentBlock[]
}

export interface TurnCompleteMessage {
  type: 'turn_complete'
}

export interface ClearMessage {
  type: 'clear'
}

export interface QuitMessage {
  type: 'quit'
}

export interface SceneContextMessage {
  type: 'scene_context'
  entities: Record<string, { name: string; image: string | null }>
}

export type ServerMessage = BlocksMessage | TurnCompleteMessage | ClearMessage | QuitMessage | SceneContextMessage
