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

import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Real Network Simulation',
    icon: '🌐',
    description: (
      <>
        Integrate with GNS3 and SDN controllers to simulate realistic network conditions
        including packet loss, latency variations, and complex topologies.
      </>
    ),
  },
  {
    title: 'Policy-Driven Security',
    icon: '🛡️',
    description: (
      <>
        Built-in Policy Engine enforces security rules, detects anomalies, and ensures
        compliance across all federated learning participants.
      </>
    ),
  },
  {
    title: 'Comprehensive Monitoring',
    icon: '📊',
    description: (
      <>
        Real-time dashboards track FL training progress, network performance, and system
        health with interactive visualizations and detailed metrics.
      </>
    ),
  },
  {
    title: 'Flexible FL Framework',
    icon: '🤖',
    description: (
      <>
        Support for multiple federated learning algorithms, custom models, and
        configurable client scenarios for diverse research needs.
      </>
    ),
  },
  {
    title: 'Research-Focused',
    icon: '🔬',
    description: (
      <>
        Designed specifically for researchers studying the intersection of federated
        learning and network systems with reproducible experiments.
      </>
    ),
  },
  {
    title: 'Open Source',
    icon: '🔓',
    description: (
      <>
        Fully open source with comprehensive documentation, active community support,
        and extensible architecture for custom research needs.
      </>
    ),
  },
];

function Feature({icon, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <div className={styles.featureIcon}>{icon}</div>
      </div>
      <div className="text--center padding-horiz--md">
        <h3 className={styles.featureTitle}>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function FeatureGrid() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
