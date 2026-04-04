export interface ClientSummary {
  name: string;
  dob: string | null;
  age: number | null;
  blood_type: string | null;
  conditions: string[];
}

export interface NgAction {
  action: string;
  reason: string | null;
  risk_level: string;
}

export interface DashboardStats {
  client_count: number;
  log_count_this_month: number;
  renewal_alerts: number;
}

export interface RenewalAlert {
  client_name: string;
  certificate_type: string;
  next_renewal_date: string;
  days_remaining: number;
}

export interface ActivityEntry {
  date: string;
  client_name: string;
  action: string;
  summary: string;
}

export interface ModelStatus {
  ollama_available: boolean;
  neo4j_available: boolean;
  loaded_models: string[];
  current_exclusive: string | null;
}

export interface ChatMessage {
  type: "routing" | "stream" | "model_status" | "metadata" | "done";
  content?: string;
  agent?: string;
  decision?: string;
  reason?: string;
  session_id?: string;
}

export interface SemanticSearchResult {
  score: number;
  node_label: string;
  properties: Record<string, unknown>;
}

export interface ExtractedGraph {
  nodes: { temp_id: string; label: string; properties: Record<string, unknown> }[];
  relationships: { source_temp_id: string; target_temp_id: string; type: string; properties: Record<string, unknown> }[];
}

export interface EcomapNode {
  id: string;
  label: string;
  node_label: string;
  category: string;
  color: string;
  properties: Record<string, unknown>;
}

export interface EcomapEdge {
  source: string;
  target: string;
  label: string;
}

export interface EcomapData {
  client_name: string;
  template: string;
  nodes: EcomapNode[];
  edges: EcomapEdge[];
}

export interface EcomapTemplate {
  id: string;
  name: string;
  description: string;
}

export interface MeetingRecord {
  date: string | null;
  title: string | null;
  transcript: string | null;
  note: string | null;
  client_name: string | null;
}
