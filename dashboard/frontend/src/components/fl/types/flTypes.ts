export interface FLMetric {
  timestamp: string;
  round: number;
  accuracy: number;
  loss: number;
  clients_connected: number;
  clients_total: number;
  training_complete: boolean;
  model_size_mb: number;
  status: string;
  // Enhanced metrics from FL server
  training_duration?: number;
  successful_clients?: number;
  failed_clients?: number;
  aggregation_duration?: number;
  evaluation_duration?: number;
}

export interface TrainingStatus {
  timestamp: string;
  training_active: boolean;
  current_round: number;
  latest_accuracy: number;
  latest_loss: number;
  connected_clients: number;
  training_complete: boolean;
  data_source: string;
  fl_server_available: boolean;
  collector_monitoring: boolean;
  stopped_by_policy?: boolean;  // Added field for policy-stopped training
  // Enhanced server state
  server_phase?: string; // 'idle', 'aggregating', 'evaluating', 'training'
  total_training_duration?: number;
  start_time?: string;
  rounds_remaining?: number;
  max_rounds?: number | null;
}

export interface MetricsSummary {
  totalRounds: number;
  bestAccuracy: number;
  lowestLoss: number;
  averageClientsConnected: number;
  averageModelSize: number;
  trainingDuration?: string;
  // Enhanced FL statistics
  convergenceRate?: number;
  stabilityScore?: number;
  efficiencyRating?: number;
  participationRate?: number;
  // New performance metrics
  averageRoundDuration?: number;
  fastestRound?: number;
  slowestRound?: number;
  clientReliabilityRate?: number;
  trainingEfficiency?: number; // accuracy gain per minute
  totalTrainingTime?: number;
}

export interface FLDataState {
  metrics: FLMetric[];
  trainingStatus: TrainingStatus | null;
  configuration: any | null;
  summary: MetricsSummary | null;
  loading: boolean;
  configLoading: boolean;
  refreshing: boolean;
  error: string | null;
  configError: string | null;
  lastUpdateTime: number;
} 