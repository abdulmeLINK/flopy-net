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
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  {
    path: '/flopy-net/search',
    component: ComponentCreator('/flopy-net/search', '8c8'),
    exact: true
  },
  {
    path: '/flopy-net/docs',
    component: ComponentCreator('/flopy-net/docs', 'c5c'),
    routes: [
      {
        path: '/flopy-net/docs',
        component: ComponentCreator('/flopy-net/docs', 'ab8'),
        routes: [
          {
            path: '/flopy-net/docs',
            component: ComponentCreator('/flopy-net/docs', 'c17'),
            routes: [
              {
                path: '/flopy-net/docs/',
                component: ComponentCreator('/flopy-net/docs/', '04b'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/api/collector',
                component: ComponentCreator('/flopy-net/docs/api/collector', 'ea5'),
                exact: true
              },
              {
                path: '/flopy-net/docs/api/collector-api',
                component: ComponentCreator('/flopy-net/docs/api/collector-api', '936'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/api/dashboard-api',
                component: ComponentCreator('/flopy-net/docs/api/dashboard-api', 'b0d'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/api/fl-framework',
                component: ComponentCreator('/flopy-net/docs/api/fl-framework', '9cb'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/api/networking-api',
                component: ComponentCreator('/flopy-net/docs/api/networking-api', '7b8'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/api/overview',
                component: ComponentCreator('/flopy-net/docs/api/overview', '23e'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/api/policy-engine',
                component: ComponentCreator('/flopy-net/docs/api/policy-engine', 'e2c'),
                exact: true
              },
              {
                path: '/flopy-net/docs/api/policy-engine-api',
                component: ComponentCreator('/flopy-net/docs/api/policy-engine-api', 'ff7'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/architecture/overview',
                component: ComponentCreator('/flopy-net/docs/architecture/overview', '15c'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/components/collector',
                component: ComponentCreator('/flopy-net/docs/components/collector', 'c49'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/components/dashboard',
                component: ComponentCreator('/flopy-net/docs/components/dashboard', '6f8'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/components/dashboard_new',
                component: ComponentCreator('/flopy-net/docs/components/dashboard_new', '859'),
                exact: true
              },
              {
                path: '/flopy-net/docs/components/fl-framework',
                component: ComponentCreator('/flopy-net/docs/components/fl-framework', 'd8e'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/components/networking',
                component: ComponentCreator('/flopy-net/docs/components/networking', '41e'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/components/policy-engine',
                component: ComponentCreator('/flopy-net/docs/components/policy-engine', '70b'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/components/scenarios',
                component: ComponentCreator('/flopy-net/docs/components/scenarios', '489'),
                exact: true
              },
              {
                path: '/flopy-net/docs/development/contributing',
                component: ComponentCreator('/flopy-net/docs/development/contributing', 'f9f'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/development/setup',
                component: ComponentCreator('/flopy-net/docs/development/setup', 'db8'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/getting-started/installation',
                component: ComponentCreator('/flopy-net/docs/getting-started/installation', '805'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/getting-started/quick-start',
                component: ComponentCreator('/flopy-net/docs/getting-started/quick-start', 'a5f'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/tutorials/advanced-configuration',
                component: ComponentCreator('/flopy-net/docs/tutorials/advanced-configuration', '636'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/tutorials/basic-experiment',
                component: ComponentCreator('/flopy-net/docs/tutorials/basic-experiment', '0fe'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/tutorials/custom-scenarios',
                component: ComponentCreator('/flopy-net/docs/tutorials/custom-scenarios', '6a5'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/user-guide/configuration',
                component: ComponentCreator('/flopy-net/docs/user-guide/configuration', '610'),
                exact: true
              },
              {
                path: '/flopy-net/docs/user-guide/gns3-integration',
                component: ComponentCreator('/flopy-net/docs/user-guide/gns3-integration', 'e88'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/user-guide/monitoring',
                component: ComponentCreator('/flopy-net/docs/user-guide/monitoring', 'd86'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/user-guide/policy-management',
                component: ComponentCreator('/flopy-net/docs/user-guide/policy-management', '560'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/user-guide/running-experiments',
                component: ComponentCreator('/flopy-net/docs/user-guide/running-experiments', '491'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/user-guide/troubleshooting',
                component: ComponentCreator('/flopy-net/docs/user-guide/troubleshooting', '379'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/flopy-net/docs/user-guides/running-experiments',
                component: ComponentCreator('/flopy-net/docs/user-guides/running-experiments', '35c'),
                exact: true
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '/flopy-net/',
    component: ComponentCreator('/flopy-net/', '529'),
    exact: true
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
