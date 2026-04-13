import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'TenderLens',
  tagline:
    'Submission documentation for an AI-assisted RFQ evaluation and award recommendation prototype.',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://tenderlens-docs.example.com',
  baseUrl: '/',
  onBrokenLinks: 'throw',

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
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      defaultMode: 'light',
      disableSwitch: false,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'TenderLens',
      items: [
        {
          to: '/docs/overview',
          position: 'left',
          label: 'Overview',
        },
        {
          to: '/docs/evaluation-approach',
          position: 'left',
          label: 'Evaluation',
        },
        {
          to: '/docs/end-to-end-flow',
          position: 'left',
          label: 'System Flow',
        },
        {
          to: '/docs/tradeoffs-and-limitations',
          position: 'left',
          label: 'Tradeoffs',
        },
        {
          to: '/docs/demo-video-script',
          position: 'left',
          label: 'Demo Script',
        },
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'right',
          label: 'Technical Appendix',
        },
      ],
    },
    footer: {
      style: 'light',
      links: [
        {
          title: 'Submission',
          items: [
            {
              label: 'Overview',
              to: '/docs/overview',
            },
            {
              label: 'Evaluation Approach',
              to: '/docs/evaluation-approach',
            },
            {
              label: 'End-to-End Flow',
              to: '/docs/end-to-end-flow',
            },
            {
              label: 'Tradeoffs and Limitations',
              to: '/docs/tradeoffs-and-limitations',
            },
            {
              label: 'What I Would Build Next',
              to: '/docs/what-i-would-build-next',
            },
            {
              label: 'Demo Video Script',
              to: '/docs/demo-video-script',
            },
          ],
        },
        {
          title: 'Appendix',
          items: [
            {
              label: 'Implementation Pipeline',
              to: '/docs/technical-appendix/implementation-pipeline',
            },
            {
              label: 'Architecture & Deployment',
              to: '/docs/technical-appendix/architecture-and-deployment',
            },
            {
              label: 'Design Decisions & Tradeoffs',
              to: '/docs/technical-appendix/design-decisions-and-tradeoffs',
            },
          ],
        },
        {
          title: 'Author',
          items: [
            {
              label: 'Archit Mishra',
              href: 'https://archit-mishra.com/',
            },
          ],
        },
      ],
      copyright: `Built by Archit Mishra · ${new Date().getFullYear()} · TenderLens submission documentation.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
