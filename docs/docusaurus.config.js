// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'FLOPY-NET',
  tagline: 'Federated Learning Observatory Platform',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://abdulmelink.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'abdulmelink', // Usually your GitHub org/user name.
  projectName: 'FLOPY-NET', // Usually your repo name.
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to set it to `zh-Hans`.
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({        docs: {
          sidebarPath: './sidebars.js',
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/abdulmelink/flopy-net/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/flopy-net-social-card.jpg',
      navbar: {
        title: 'FLOPY-NET',
        logo: {
          src: 'img/logo.svg',
        },        
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            href: 'https://github.com/abdulmelink/flopy-net',
            label: 'GitHub',
            position: 'right',
          },
          {
            href: 'https://abdulmelink.github.io/flopy-net/',
            label: 'Live Demo',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',        links: [
          {
            title: 'Documentation',
            items: [
              {
                label: 'Getting Started',
                to: '/docs/getting-started/installation',
              },
              {
                label: 'Architecture',
                to: '/docs/architecture/overview',
              },
              {
                label: 'API Reference',
                to: '/docs/api/overview',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub Issues',
                href: 'https://github.com/abdulmelink/flopy-net/issues',
              },
              {
                label: 'GitHub Discussions',
                href: 'https://github.com/abdulmelink/flopy-net/discussions',
              },
            ],
          },
          {            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/abdulmelink/flopy-net',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Abdulmelik Saylan. FLOPY-NET is open source under the MIT License.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['python', 'json', 'yaml', 'docker', 'bash'],
      },
      colorMode: {
        defaultMode: 'dark',
        disableSwitch: false,
        respectPrefersColorScheme: false,
      },
      algolia: {
        // The application ID provided by Algolia
        appId: 'YOUR_APP_ID',
        // Public API key: it is safe to commit it
        apiKey: 'YOUR_SEARCH_API_KEY',
        indexName: 'flopy-net',
        // Optional: see doc section below
        contextualSearch: true,
      },
    }),
};

export default config;
