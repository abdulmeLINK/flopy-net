# FLOPY-NET Policy Definitions

This directory contains policy definitions for the FLOPY-NET Policy Engine (Flask service at 192.168.100.20:5000), which enforces rules and security policies across all federated learning and network components in the containerized architecture.

## Policy Engine Integration

The Policy Engine operates as a centralized Docker container (`abdulmelink/flopynet-policy-engine:v1.0.0-alpha.8`) that:
- Loads policies from JSON files in this directory
- Provides REST API endpoints for policy queries and enforcement
- Maintains real-time event buffers for policy evaluation
- Integrates with FL Server, FL Clients, SDN Controller, and Collector services

## Active Policy Configuration

**Primary Policy File**: `policies.json`

This is the main active policy file used by the Policy Engine in the Docker Compose setup. The Policy Engine container is configured via environment variables:

```yaml
environment:
  - POLICY_CONFIG=/app/config/policies/policy_config.json
  - POLICY_FUNCTIONS_DIR=/app/config/policy_functions
```

**To modify system-wide policies, edit `policies.json`.**

## Container Integration

The Policy Engine integrates with FLOPY-NET services as follows:

### FL Server Integration (192.168.100.10:8080)
- **Client Authorization**: Validates FL client participation requests
- **Model Aggregation Policies**: Controls which client updates are accepted
- **Training Round Policies**: Manages training round progression and client selection

### FL Client Integration (192.168.100.101-102)
- **Participation Policies**: Determines client eligibility for training rounds
- **Data Privacy Policies**: Enforces data protection and sharing restrictions
- **Resource Usage Policies**: Controls computational resource allocation

### SDN Controller Integration (192.168.100.41:6633/8181)
- **Network Policies**: Controls traffic flow and QoS through OpenFlow rules
- **Security Policies**: Implements network-level access control and isolation
- **Performance Policies**: Manages bandwidth allocation and latency requirements

### Collector Integration (192.168.100.40:8000)
- **Monitoring Policies**: Defines metrics collection frequency and retention
- **Alert Policies**: Triggers notifications based on system conditions
- **Compliance Policies**: Ensures regulatory adherence and audit trail creation

## Policy File Structure

```json
{
  "policies": [
    {
      "name": "fl_client_participation_policy",
      "type": "federated_learning",
      "conditions": {
        "client_trust_score": "> 0.7",
        "network_latency": "< 100ms"
      },
      "actions": {
        "allow_participation": true,
        "log_decision": true
      },
      "enabled": true
    },
    {
      "name": "network_qos_policy", 
      "type": "network",
      "conditions": {
        "fl_training_active": true
      },
      "actions": {
        "set_priority": "high",
        "reserve_bandwidth": "50%"
      },
      "enabled": true
    }
  ]
}
```
- **Anomaly Detection**: Behavioral anomaly detection rules
- **Access Control**: Resource access permissions

### Federated Learning Policies
- **Client Participation**: Rules for client participation in FL rounds
- **Model Validation**: Model size, complexity, and performance constraints
- **Data Privacy**: Data handling and privacy protection rules
- **Training Parameters**: Learning rate, batch size, and other training constraints

### Network Policies
- **Traffic Management**: Network traffic rules and QoS policies
- **Bandwidth Allocation**: Bandwidth limits and priorities
- **Connection Security**: Secure connection requirements
- **Resource Usage**: Network resource utilization limits

### System Policies
- **Resource Management**: CPU, memory, and storage limits
- **Component Integration**: Inter-component communication rules
- **Monitoring**: Logging and metrics collection policies
- **Maintenance**: System maintenance and update policies

## Policy Engine Integration

The Policy Engine enforces policies through:

1. **Component Queries**: Other services query the Policy Engine for permission checks
2. **Real-time Monitoring**: Continuous policy compliance monitoring
3. **Event-driven Actions**: Automatic responses to policy violations
4. **Dashboard Integration**: Policy status visualization and management

## Policy Development

### Creating New Policies

1. **Define Policy Structure**: Specify conditions, actions, and metadata
2. **Test Policy Logic**: Validate policy behavior in test environment
3. **Add to Policy File**: Insert policy into `policies.json`
4. **Verify Integration**: Ensure Policy Engine processes the new policy correctly

### Policy Testing

- **Unit Tests**: Test individual policy rules and conditions
- **Integration Tests**: Test policy enforcement across components
- **Scenario Tests**: Validate policies in realistic scenarios
- **Performance Tests**: Monitor policy evaluation performance

## Custom Policy Functions

Custom policy functions are defined in `config/policy_functions/`:

- **`model_size_policy.json`**: Example policy function for model size validation
- Custom functions can be added following the same pattern

## Policy Compliance and Monitoring

The Policy Engine provides:

- **Real-time Compliance**: Continuous policy compliance checking
- **Violation Logging**: Detailed logging of policy violations
- **Dashboard Integration**: Policy status and compliance visualization
- **Alerting**: Notifications for critical policy violations

## Best Practices

### Policy Design
- **Clear Conditions**: Define precise, testable policy conditions
- **Appropriate Actions**: Specify proportional responses to violations
- **Performance**: Keep policy evaluation efficient
- **Documentation**: Document policy purpose and behavior

### Policy Management
- **Version Control**: Track policy changes over time
- **Testing**: Thoroughly test policies before deployment
- **Monitoring**: Monitor policy performance and effectiveness
- **Review**: Regularly review and update policies

### Security Considerations
- **Least Privilege**: Apply minimum necessary restrictions
- **Defense in Depth**: Layer multiple complementary policies
- **Audit Trail**: Maintain comprehensive policy audit logs
- **Regular Updates**: Keep policies current with system changes

For detailed policy schema and implementation details, refer to the Policy Engine documentation.