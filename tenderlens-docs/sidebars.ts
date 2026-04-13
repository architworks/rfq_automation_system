import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'overview',
    'evaluation-approach',
    'end-to-end-flow',
    'tradeoffs-and-limitations',
    'what-i-would-build-next',
    'demo-video-script',
    {
      type: 'category',
      label: 'Technical Appendix',
      items: [
        'technical-appendix/implementation-pipeline',
        'technical-appendix/architecture-and-deployment',
        'technical-appendix/design-decisions-and-tradeoffs',
      ],
    },
  ],
};

export default sidebars;
