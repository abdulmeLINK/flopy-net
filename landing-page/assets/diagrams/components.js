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

// Mermaid diagram definitions for FLOPY-NET landing page

// Initialize Mermaid with GitHub-inspired futuristic theme
mermaid.initialize({
    theme: 'base',
    themeVariables: {
        // Background and main colors (GitHub-inspired)
        primaryColor: '#79c0ff',
        primaryTextColor: '#f0f6fc',
        primaryBorderColor: '#58a6ff',
        lineColor: '#79c0ff',
        secondaryColor: '#21262d',
        tertiaryColor: '#161b22',
        background: 'transparent',
        
        // Node styling with gradient-like colors
        mainBkg: '#21262d',
        secondBkg: '#30363d',
        tertiaryBkg: '#161b22',
        
        // Text styling
        textColor: '#f0f6fc',
        darkTextColor: '#0d1117',
        
        // Border and edge styling
        edgeLabelBackground: 'rgba(13, 17, 23, 0.95)',
        clusterBg: 'rgba(33, 38, 45, 0.4)',
        clusterBorder: '#58a6ff',
        
        // Different node type colors (GitHub color palette)
        fillType0: '#21262d',
        fillType1: '#30363d',
        fillType2: '#39414a',
        fillType3: '#79c0ff',
        
        // Special accent colors
        cScale0: '#79c0ff', // Neon blue
        cScale1: '#d2a8ff', // Neon purple  
        cScale2: '#ffa7c4', // Neon pink
        cScale3: '#7ce38b', // Neon green
        cScale4: '#ffd700', // Neon yellow
        
        // Control plane colors
        controlColor: '#30363d',
        controlBorder: '#79c0ff',
        
        // Data plane colors
        dataColor: '#21262d',
        dataBorder: '#d2a8ff'
    },
    startOnLoad: true,
    securityLevel: 'loose',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif',
    fontSize: 16,    flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis',
        // FIXED: Optimized spacing for proper positioning without overflow
        nodeSpacing: 120, // Reasonable spacing that prevents overflow
        rankSpacing: 140, // Proper vertical spacing
        padding: 40, // Balanced padding for good centering
        diagramPadding: 30, // Appropriate diagram padding
        subGraphTitleMargin: 20, // Reasonable title margin
        titleTopMargin: 15,
        // FIXED: Ensure stable positioning
        arrowMarkerAbsolute: false,
        fontSize: 14, // Appropriate font size for readability
        wrapEnabled: true,
        wrap: true,
        // FIXED: Center alignment without forcing oversized elements
        align: 'center',
        direction: 'TB'
    },
    graph: {
        padding: 50, // Increased for better spacing
        useMaxWidth: true
    }
});

// Deployment stack diagram configuration
const deploymentDiagram = `
flowchart TD
    subgraph Cloud["Cloud Registry"]
        Registry["abdulmelink/flopynet-*<br/>Container Images"]
    end
    
    subgraph GNS3Env["GNS3 Virtual Environment"]
        direction TB
        subgraph ContainerLayer["Application Layer"]
            PolicyEngine["Policy Engine<br/>Governance & Rules<br/>Decision Authority"]
            FLServer["FL Server<br/>Model Coordination<br/>Global Aggregation"]
            FLClients["FL Clients<br/>Distributed Training<br/>Edge Computing"]
        end
        
        subgraph RuntimeLayer["Container Runtime"]
            Docker["Docker Engine<br/>Container Orchestration<br/>Resource Management"]
        end
        
        subgraph SystemLayer["Virtualization Layer"]
            GNS3VM["GNS3 Virtual Machine<br/>Network Simulation<br/>SDN Integration"]
        end
        
        subgraph InfraLayer["Infrastructure Foundation"]
            Hardware["Physical Resources<br/>Compute & Storage<br/>Network Fabric"]
        end
        
        ContainerLayer --> RuntimeLayer
        RuntimeLayer --> SystemLayer
        SystemLayer --> InfraLayer
    end
    
    Registry -.->|"Container Pull<br/>Image Distribution"| ContainerLayer
    
    classDef registryStyle fill:#21262d,stroke:#79c0ff,stroke-width:3px,color:#f0f6fc,stroke-dasharray: 5 5
    classDef containerStyle fill:#30363d,stroke:#d2a8ff,stroke-width:2px,color:#f0f6fc
    classDef runtimeStyle fill:#39414a,stroke:#ffa7c4,stroke-width:2px,color:#f0f6fc
    classDef systemStyle fill:#30363d,stroke:#7ce38b,stroke-width:2px,color:#f0f6fc
    classDef infraStyle fill:#21262d,stroke:#58a6ff,stroke-width:2px,color:#f0f6fc
    classDef subgraphStyle fill:rgba(45,55,72,0.1),stroke:#79c0ff,stroke-width:2px
    
    class Registry registryStyle
    class PolicyEngine,FLServer,FLClients containerStyle
    class Docker runtimeStyle
    class GNS3VM systemStyle
    class Hardware infraStyle
`;

// Control plane diagram configuration
const controlPlaneDiagram = `
flowchart TB    subgraph ControlPlane["Control Plane"]
        direction LR
        PE["Policy Engine<br/>Rules & Governance<br/>Decision Making"]
        Dashboard["Dashboard<br/>Real-time Monitoring<br/>Analytics Hub"]
        SDN["SDN Controller<br/>Network Management<br/>Traffic Control"]
    end
    
    subgraph DataPlane["Data & Emulation Plane"]
        direction TB
        subgraph NetworkInfra["Network Infrastructure"]
            GNS3["GNS3 Network<br/>Virtual Topology<br/>SDN Switches"]
        end
        
        subgraph MLWorkload["Machine Learning Workload"]
            FLServer["FL Server<br/>Global Model<br/>Aggregation"]
            
            subgraph ClientCluster["Client Ecosystem"]
                Client1["FL Client Alpha<br/>Edge Device<br/>Local Training"]
                Client2["FL Client Beta<br/>Mobile Device<br/>Model Updates"]
                Client3["FL Client Gamma<br/>IoT Sensor<br/>Data Processing"]
            end
        end
    end
    
    %% Control relationships
    PE -.->|"Policy Enforcement"| FLServer
    PE -.->|"Rule Validation"| Client1
    PE -.->|"Rule Validation"| Client2
    PE -.->|"Rule Validation"| Client3
    
    SDN -.->|"Traffic Shaping"| GNS3
    SDN -.->|"Network Control"| NetworkInfra
    
    Dashboard -.->|"Metrics Collection"| PE
    Dashboard -.->|"Network Monitoring"| GNS3
    Dashboard -.->|"Performance Analysis"| MLWorkload
    
    %% Data flow relationships
    FLServer <-->|"Model Exchange<br/>Federated Updates"| Client1
    FLServer <-->|"Model Exchange<br/>Federated Updates"| Client2
    FLServer <-->|"Model Exchange<br/>Federated Updates"| Client3
    
    MLWorkload -.->|"Network Traffic"| NetworkInfra
    
    classDef controlStyle fill:#30363d,stroke:#79c0ff,stroke-width:3px,color:#f0f6fc
    classDef dataStyle fill:#21262d,stroke:#d2a8ff,stroke-width:2px,color:#f0f6fc
    classDef serverStyle fill:#39414a,stroke:#58a6ff,stroke-width:3px,color:#f0f6fc
    classDef clientStyle fill:#30363d,stroke:#7ce38b,stroke-width:2px,color:#f0f6fc
    classDef networkStyle fill:#21262d,stroke:#ffa7c4,stroke-width:2px,color:#f0f6fc
    
    class PE,Dashboard,SDN controlStyle
    class FLServer serverStyle
    class Client1,Client2,Client3 clientStyle
    class GNS3 networkStyle
`;

// Export for use in other scripts
window.flopynetDiagrams = {
    deployment: deploymentDiagram,
    controlPlane: controlPlaneDiagram
};
