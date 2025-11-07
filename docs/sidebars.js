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

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */

// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  // By default, Docusaurus generates a sidebar from the docs folder structure
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/installation',
        'getting-started/quick-start',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
      ],
    },
    {
      type: 'category',
      label: 'Components',
      items: [
        'components/dashboard',
        'components/fl-framework',
        'components/collector',
        'components/policy-engine',
        'components/networking',
      ],
    },
    {
      type: 'category',
      label: 'User Guide',
      items: [
        'user-guide/running-experiments',
        'user-guide/monitoring',
        'user-guide/policy-management',
        'user-guide/gns3-integration',
        'user-guide/troubleshooting',
      ],
    },
    {
      type: 'category',      label: 'API Reference',
      items: [
        'api/overview',
        'api/fl-framework',
        'api/policy-engine-api',
        'api/collector',
        'api/dashboard-api',
        'api/networking-api',
      ],
    },
    {
      type: 'category',
      label: 'Tutorials',
      items: [
        'tutorials/basic-experiment',
        'tutorials/custom-scenarios',
        'tutorials/advanced-configuration',
      ],
    },
    {
      type: 'category',
      label: 'Development',
      items: [
        'development/setup',
        'development/contributing',
      ],
    },
  ],
};

export default sidebars;
