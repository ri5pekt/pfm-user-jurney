export interface TrackingEvent {
  session_id: string;
  page_url: string;
  referrer?: string;
  user_agent?: string;
}

export interface EventRow extends TrackingEvent {
  id: number;
  referrer: string;
  user_agent: string;
  timestamp: Date;
}

export interface JourneyNode {
  id: string;
  label: string;
  traffic_source: string;
  visit_count: number;
}

export interface JourneyEdge {
  source: string;
  target: string;
  count: number;
}
