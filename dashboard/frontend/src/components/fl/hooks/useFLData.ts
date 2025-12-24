/**
 * Copyright (c) 2025 Abdulmelik Saylan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getFLConfiguration, FLConfiguration } from '../../../services/flMonitoringApi';
import { FLMetric, TrainingStatus, MetricsSummary, FLDataState } from '../types/flTypes';

export const useFLData = () => {
  const isMountedRef = useRef(true);
  const [state, setState] = useState<FLDataState>({
    metrics: [],
    trainingStatus: null,
    configuration: null,
    summary: null,
    loading: true,
    configLoading: true,
    refreshing: false,
    error: null,
    configError: null,
    lastUpdateTime: Date.now()
  });

  // Utility functions
  const formatAccuracy = useCallback((accuracy: number): string => {
    return `${(accuracy * 100).toFixed(2)}%`;
  }, []);

  const formatLoss = useCallback((loss: number): string => {
    return loss.toFixed(4);
  }, []);

  const formatModelSize = useCallback((sizeInMB: number): string => {
    if (sizeInMB >= 1024) {
      return `${(sizeInMB / 1024).toFixed(2)} GB`;
    } else if (sizeInMB >= 1) {
      return `${sizeInMB.toFixed(2)} MB`;
    } else {
      return `${(sizeInMB * 1024).toFixed(2)} KB`;
    }
  }, []);

  const getTrainingStatusColor = useCallback((): 'success' | 'warning' | 'error' | 'info' => {
    if (!state.trainingStatus) return 'error';
    
    if (state.trainingStatus.stopped_by_policy) {
      return 'warning';
    } else if (state.trainingStatus.training_complete) {
      return 'success';
    } else if (state.trainingStatus.training_active) {
      if (state.trainingStatus.connected_clients === 0) {
        return 'warning';
      }
      return 'success';  // Changed from 'info' to 'success' for green color
    } else if (state.trainingStatus.fl_server_available) {
      return 'info';  // Changed from 'warning' to 'info' for blue color
    } else {
      return 'error';
    }
  }, [state.trainingStatus]);

  const getTrainingStatusText = useCallback((): string => {
    if (!state.trainingStatus) return 'Unknown';
    
    if (state.trainingStatus.stopped_by_policy) {
      return 'Stopped by Policy';
    } else if (state.trainingStatus.training_complete) {
      return 'Training Complete';
    } else if (state.trainingStatus.training_active) {
      if (state.trainingStatus.connected_clients === 0) {
        return 'Training Active (No Clients)';
      }
      const phase = state.trainingStatus.server_phase;
      if (phase === 'aggregating') {
        return 'Aggregating Models';
      } else if (phase === 'evaluating') {
        return 'Evaluating Model';
      } else {
        return 'Training Active';
      }
    } else if (state.trainingStatus.fl_server_available) {
      return 'Server Ready';
    } else {
      return 'Server Offline';
    }
  }, [state.trainingStatus]);

  // Calculate summary statistics
  const calculateSummary = useCallback((data: FLMetric[], currentStatus?: TrainingStatus): MetricsSummary => {
    if (data.length === 0) {
      return {
        totalRounds: 0,
        bestAccuracy: 0,
        lowestLoss: 0,
        averageClientsConnected: 0,
        averageModelSize: 0,
        convergenceRate: 0,
        stabilityScore: 0,
        efficiencyRating: 0,
        participationRate: 0,
        averageRoundDuration: 0,
        fastestRound: 0,
        slowestRound: 0,
        clientReliabilityRate: 0,
        trainingEfficiency: 0,
        totalTrainingTime: 0
      };
    }

    const validAccuracies = data.map(d => d.accuracy).filter(a => a > 0);
    const validLosses = data.map(d => d.loss).filter(l => l > 0);
    
    // Extract client data from historical rounds - NO FALLBACKS
    const clientConnectedCounts = data.map(d => d.clients_connected || 0).filter(c => c > 0);
    const clientTotalCounts = data.map(d => d.clients_total || 0).filter(c => c > 0);
    
    console.log('📊 Client data availability analysis:', {
      totalRounds: data.length,
      roundsWithClientData: clientConnectedCounts.length,
      dataAvailabilityPercentage: data.length > 0 ? (clientConnectedCounts.length / data.length * 100).toFixed(1) + '%' : '0%',
      clientConnectedRange: clientConnectedCounts.length > 0 ? [Math.min(...clientConnectedCounts), Math.max(...clientConnectedCounts)] : 'No data',
      sampleRounds: data.slice(0, 3).map(d => ({ 
        round: d.round, 
        clients_connected: d.clients_connected || 'Not provided', 
        clients_total: d.clients_total || 'Not provided' 
      }))
    });
    
    // Calculate client metrics ONLY if we have sufficient historical data
    let averageClientsConnected = 0;
    let participationRate = 0;
    let clientReliabilityRate = 0;
    
    // Require at least 3 rounds of data to calculate meaningful statistics
    const minimumRoundsRequired = 3;
    
    if (clientConnectedCounts.length >= minimumRoundsRequired) {
      // We have sufficient historical data for accurate calculations
      averageClientsConnected = Math.round(clientConnectedCounts.reduce((a, b) => a + b, 0) / clientConnectedCounts.length);
      
      // Calculate participation rate as the consistency of client participation
      const maxClients = Math.max(...clientConnectedCounts);
      const minClients = Math.min(...clientConnectedCounts);
      const avgConnected = averageClientsConnected;
      
      // Participation rate: how close to maximum participation we maintain on average
      participationRate = maxClients > 0 ? (avgConnected / maxClients) * 100 : 0;
      
      // Client reliability rate: consistency of client participation (1 - coefficient of variation)
      if (clientConnectedCounts.length > 1) {
        const mean = avgConnected;
        const variance = clientConnectedCounts.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / clientConnectedCounts.length;
        const stdDev = Math.sqrt(variance);
        const coefficientOfVariation = mean > 0 ? stdDev / mean : 1;
        clientReliabilityRate = Math.max(0, (1 - coefficientOfVariation) * 100);
      } else {
        clientReliabilityRate = 100; // Perfect reliability if only one data point (but we need 3+ anyway)
      }
      
      console.log('✅ Client metrics calculated from historical data:', {
        roundsUsed: clientConnectedCounts.length,
        averageClientsConnected,
        participationRate: participationRate.toFixed(1) + '%',
        clientReliabilityRate: clientReliabilityRate.toFixed(1) + '%'
      });
    } else {
      // Insufficient historical data - DO NOT USE FALLBACKS
      console.warn(`⚠️ Insufficient client data for reliable statistics: ${clientConnectedCounts.length}/${data.length} rounds have client data (need at least ${minimumRoundsRequired})`);
      
      // Set special values to indicate data is not available (not 0, which implies measurement)
      averageClientsConnected = clientConnectedCounts.length > 0 ? 
        Math.round(clientConnectedCounts.reduce((a, b) => a + b, 0) / clientConnectedCounts.length) : 
        -1; // -1 indicates "not available" vs 0 which indicates "measured as zero"
      participationRate = -1; // -1 indicates "cannot calculate"
      clientReliabilityRate = -1; // -1 indicates "cannot calculate"
    }
    
    // Extract model sizes from server data - NO FALLBACKS
    const modelSizes = data.map(d => d.model_size_mb || 0).filter(s => s > 0);
    
    const roundNumbers = data.map(d => d.round).filter(r => r > 0);
    const totalRounds = data.length; // Count of actual rounds, not max round number
    
    const bestAccuracy = validAccuracies.length > 0 ? Math.max(...validAccuracies) : 0;
    const lowestLoss = validLosses.length > 0 ? Math.min(...validLosses) : 0;
    
    // Calculate averages only from actual server data - NO FALLBACKS
    const averageModelSize = modelSizes.length > 0 ? 
      modelSizes.reduce((a, b) => a + b, 0) / modelSizes.length : 
      -1; // -1 indicates "not provided by system"

    // Calculate training durations for enhanced metrics
    const trainingDurations = data.map(d => d.training_duration || 0).filter(t => t > 0);
    const averageRoundDuration = trainingDurations.length > 0 ?
      trainingDurations.reduce((a, b) => a + b, 0) / trainingDurations.length : 0;
    const fastestRound = trainingDurations.length > 0 ? Math.min(...trainingDurations) : 0;
    const slowestRound = trainingDurations.length > 0 ? Math.max(...trainingDurations) : 0;
    const totalTrainingTime = trainingDurations.reduce((a, b) => a + b, 0);

    // Enhanced statistics calculations - only if we have sufficient data
    let convergenceRate = 0;
    let stabilityScore = 0;
    let efficiencyRating = 0;
    let trainingEfficiency = 0;

    if (validAccuracies.length >= 3) {
      const recentStart = Math.max(0, validAccuracies.length - 3);
      const recentAccuracies = validAccuracies.slice(recentStart);
      const earlyAccuracies = validAccuracies.slice(0, Math.min(3, validAccuracies.length));
      
      if (earlyAccuracies.length > 0 && recentAccuracies.length > 0) {
        const earlyAvg = earlyAccuracies.reduce((a, b) => a + b, 0) / earlyAccuracies.length;
        const recentAvg = recentAccuracies.reduce((a, b) => a + b, 0) / recentAccuracies.length;
        convergenceRate = Math.max(0, (recentAvg - earlyAvg) * 100);
      }

      if (recentAccuracies.length > 1) {
        const mean = recentAccuracies.reduce((a, b) => a + b, 0) / recentAccuracies.length;
        const variance = recentAccuracies.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / recentAccuracies.length;
        const stdDev = Math.sqrt(variance);
        const cv = mean > 0 ? stdDev / mean : 1;
        stabilityScore = Math.max(0, Math.min(100, (1 - cv) * 100));
      }
    } else {
      // Insufficient data for convergence and stability calculations
      convergenceRate = -1; // -1 indicates "cannot calculate"
      stabilityScore = -1; // -1 indicates "cannot calculate"
    }

    if (totalRounds > 0 && bestAccuracy > 0) {
      const accuracyGain = validAccuracies.length > 1 ? 
        (validAccuracies[validAccuracies.length - 1] - validAccuracies[0]) : bestAccuracy;
      efficiencyRating = Math.min(100, (accuracyGain * 100) / totalRounds * 10);
    } else {
      efficiencyRating = -1; // -1 indicates "cannot calculate"
    }

    // Training efficiency: accuracy improvement per minute
    if (totalTrainingTime > 0 && validAccuracies.length > 1) {
      const accuracyImprovement = validAccuracies[validAccuracies.length - 1] - validAccuracies[0];
      trainingEfficiency = (accuracyImprovement * 100) / (totalTrainingTime / 60);
    } else {
      trainingEfficiency = -1; // -1 indicates "cannot calculate"
    }

    const result = {
      totalRounds,
      bestAccuracy,
      lowestLoss,
      averageClientsConnected,
      averageModelSize,
      convergenceRate: convergenceRate >= 0 ? Math.round(convergenceRate * 100) / 100 : -1,
      stabilityScore: stabilityScore >= 0 ? Math.round(stabilityScore * 100) / 100 : -1,
      efficiencyRating: efficiencyRating >= 0 ? Math.round(efficiencyRating * 100) / 100 : -1,
      participationRate: participationRate >= 0 ? Math.round(participationRate * 100) / 100 : -1,
      averageRoundDuration,
      fastestRound,
      slowestRound,
      clientReliabilityRate: clientReliabilityRate >= 0 ? Math.round(clientReliabilityRate * 100) / 100 : -1,
      trainingEfficiency: trainingEfficiency >= 0 ? Math.round(trainingEfficiency * 1000) / 1000 : -1,
      totalTrainingTime
    };

    console.log('📈 Summary statistics calculated (transparent data availability):', {
      dataAvailable: {
        clientMetrics: clientConnectedCounts.length >= minimumRoundsRequired,
        modelSizes: modelSizes.length > 0,
        accuracyTrends: validAccuracies.length >= 3,
        trainingDurations: trainingDurations.length > 0
      },
      calculatedValues: {
        averageClientsConnected: result.averageClientsConnected,
        participationRate: result.participationRate === -1 ? 'Not available' : result.participationRate + '%',
        clientReliabilityRate: result.clientReliabilityRate === -1 ? 'Not available' : result.clientReliabilityRate + '%',
        averageModelSize: result.averageModelSize === -1 ? 'Not provided' : result.averageModelSize + ' MB'
      },
      dataPointsUsed: {
        clientConnectedCounts: clientConnectedCounts.length,
        modelSizes: modelSizes.length,
        validAccuracies: validAccuracies.length,
        trainingDurations: trainingDurations.length
      }
    });

    return result;
  }, []);

  // Load FL data
  const loadData = useCallback(async (showLoadingSpinner = false) => {
    if (!isMountedRef.current) return;
    
    try {
      setState(prev => ({
        ...prev,
        loading: showLoadingSpinner ? true : prev.loading,
        refreshing: !showLoadingSpinner,
        error: null
      }));

      const [statusResponse, metricsResponse] = await Promise.allSettled([
        fetch('/api/fl-monitoring/metrics/fl/status'),
        fetch('/api/fl-monitoring/metrics/fl/rounds?limit=1000&include_rounds=true&consolidate_rounds=true')
      ]);

      if (!isMountedRef.current) return;

      let newTrainingStatus = null;
      let newMetrics: FLMetric[] = [];

      // Handle training status
      if (statusResponse.status === 'fulfilled' && statusResponse.value.ok) {
        const statusData = await statusResponse.value.json();
        
        newTrainingStatus = {
          ...statusData,
          max_rounds: statusData.max_rounds || 0
        };
      } else {
        console.warn('Failed to load training status');
      }

      // Handle FL metrics
      if (metricsResponse.status === 'fulfilled' && metricsResponse.value.ok) {
        const metricsData = await metricsResponse.value.json();
        newMetrics = metricsData.rounds || metricsData.metrics || [];
        console.log(`✅ FL Metrics loaded: ${newMetrics.length} rounds from response:`, {
          hasRounds: !!metricsData.rounds,
          hasMetrics: !!metricsData.metrics,
          totalRounds: metricsData.total_rounds,
          latestRound: metricsData.latest_round,
          sampleMetric: newMetrics[0]
        });
      } else {
        console.warn('Failed to load FL metrics');
      }

      // Calculate summary
      const newSummary = newMetrics.length > 0 ? calculateSummary(newMetrics, newTrainingStatus) : null;

      setState(prev => ({
        ...prev,
        metrics: newMetrics,
        trainingStatus: newTrainingStatus,
        summary: newSummary,
        loading: false,
        refreshing: false,
        lastUpdateTime: Date.now()
      }));

    } catch (err) {
      if (!isMountedRef.current) return;
      console.error('Error loading FL data:', err);
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to load data',
        loading: false,
        refreshing: false
      }));
    }
  }, [calculateSummary]);

  // Load configuration
  const loadConfiguration = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    try {
      setState(prev => ({
        ...prev,
        configLoading: true,
        configError: null
      }));

      const configData = await getFLConfiguration();
      
      if (!isMountedRef.current) return;
      
      setState(prev => ({
        ...prev,
        configuration: configData,
        configLoading: false
      }));
      
      console.log('✅ FL Configuration loaded successfully:', configData.status);
    } catch (err) {
      if (!isMountedRef.current) return;
      console.error('❌ Error loading FL configuration:', err);
      setState(prev => ({
        ...prev,
        configError: err instanceof Error ? err.message : 'Failed to load configuration',
        configLoading: false
      }));
    }
  }, []);

  // Refresh function
  const handleRefresh = useCallback(() => {
    loadData(false);
  }, [loadData]);

  // Initial load and auto refresh
  useEffect(() => {
    loadData(true);
    loadConfiguration();

    const refreshInterval = setInterval(() => {
      loadData(false);
    }, 5000); // Refresh every 5 seconds

    return () => {
      clearInterval(refreshInterval);
      isMountedRef.current = false;
    };
  }, [loadData, loadConfiguration]);

  return {
    ...state,
    // Actions
    handleRefresh,
    loadConfiguration,
    // Utilities
    formatAccuracy,
    formatLoss,
    formatModelSize,
    getTrainingStatusColor,
    getTrainingStatusText
  };
}; 