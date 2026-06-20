// Content block types (matching Python render.py)

export interface EntityInfo {
  id: string;
  name: string;
  behaviors: string[];
}

export interface ExitDetail {
  direction: string;
  destination: string;
}

export interface RoomEnterBlock {
  type: "room_enter";
  room_id: string;
  name: string;
  description: string;
  exits: ExitDetail[];
  objects: EntityInfo[];
  inventory: EntityInfo[];
  image: string | null;
}

export interface ActionResultBlock {
  type: "action_result";
  text: string;
}

export interface NarrateBlock {
  type: "narrate";
  text: string;
}

export interface SpeakBlock {
  type: "speak";
  text: string;
  speaker: string | null;
  manner: string | null;
}

export interface ThinkBlock {
  type: "think";
  text: string;
}

export interface AmbientBlock {
  type: "ambient";
  text: string;
}

export interface RevealBlock {
  type: "reveal";
  text: string;
  entity: string | null;
}

export interface FocusBlock {
  type: "focus";
  text: string;
  entity: string | null;
}

export interface SfxBlock {
  type: "sfx";
  text: string;
}

export interface ImageBlock {
  type: "image";
  src: string;
  alt: string;
  layout: "inline" | "float-left" | "float-right" | "background";
  size: "small" | "medium" | "large" | "full";
}

export interface SystemMessageBlock {
  type: "system";
  text: string;
  level: "info" | "warning" | "error";
}

export interface CommandBlock {
  type: "command";
  text: string;
}

export interface DebugBlock {
  type: "debug";
  label: string;
  content: string;
}

export type ContentBlock =
  | RoomEnterBlock
  | ActionResultBlock
  | NarrateBlock
  | SpeakBlock
  | ThinkBlock
  | AmbientBlock
  | RevealBlock
  | FocusBlock
  | SfxBlock
  | ImageBlock
  | SystemMessageBlock
  | CommandBlock
  | DebugBlock;

// Presentation intent: the LLM's pacing for a block; the engine maps it to size.
export type Beat = "aside" | "normal" | "emphasis";

// Renderable block: a ContentBlock with optional metadata stamped at insert time
export type RenderableBlock = ContentBlock & {
  _side?: "image-left" | "image-right";
  beat?: Beat | null;
};

// Server messages
export interface BlocksMessage {
  type: "blocks";
  blocks: ContentBlock[];
}

export interface TurnCompleteMessage {
  type: "turn_complete";
}

export interface ClearMessage {
  type: "clear";
}

export interface QuitMessage {
  type: "quit";
}

export interface SceneContextMessage {
  type: "scene_context";
  entities: Record<string, { name: string; image: string | null }>;
}

export interface StateUpdateMessage {
  type: "state_update";
  exits: ExitDetail[];
  objects: EntityInfo[];
  inventory: EntityInfo[];
}

export interface StateContextMessage {
  type: "state-context";
  content: string;
}

export interface SavesListMessage {
  type: "saves-list";
  saves: { slot: string; timestamp: string }[];
}

export interface SaveResultMessage {
  type: "save-result";
  success: boolean;
  message: string;
}

export interface LoadResultMessage {
  type: "load-result";
  success: boolean;
  message: string;
}

export interface KgContextMessage {
  type: "kg-context";
  content: string;
}

export interface ThemeMessage {
  type: "theme";
  // token name (e.g. "bg", "accent-glow") -> hex; applied as --game-<token>
  swatches: Record<string, string>;
}

export type ServerMessage =
  | BlocksMessage
  | TurnCompleteMessage
  | ClearMessage
  | QuitMessage
  | SceneContextMessage
  | StateUpdateMessage
  | StateContextMessage
  | SavesListMessage
  | SaveResultMessage
  | LoadResultMessage
  | KgContextMessage
  | ThemeMessage;
