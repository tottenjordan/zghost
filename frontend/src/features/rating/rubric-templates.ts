export type ScaleType = 'likert' | 'numeric' | 'pass-fail' | 'custom';

export interface CriterionScale {
  type: ScaleType;
  min: number;
  max: number;
  labels?: Record<number, string>;
}

export interface ExtendedCriterion {
  id: string;
  name: string;
  description: string;
  weight: number;
  scale: CriterionScale;
}

export interface ExtendedRubric {
  id: string;
  name: string;
  description: string;
  criteria: ExtendedCriterion[];
}

export const DEFAULT_RUBRICS: ExtendedRubric[] = [
  {
    id: 'ad-copy-quality',
    name: 'Ad Copy Quality',
    description: 'Comprehensive evaluation of advertising copy effectiveness and brand alignment',
    criteria: [
      {
        id: 'creativity',
        name: 'Creativity',
        description: 'Originality and innovative approach to messaging',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Generic',
            2: 'Somewhat creative',
            3: 'Moderately creative',
            4: 'Very creative',
            5: 'Highly innovative',
          },
        },
      },
      {
        id: 'brand-alignment',
        name: 'Brand Alignment',
        description: 'Consistency with brand voice, values, and positioning',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Off-brand',
            2: 'Weak alignment',
            3: 'Acceptable fit',
            4: 'Strong alignment',
            5: 'Perfect embodiment',
          },
        },
      },
      {
        id: 'relevance',
        name: 'Relevance',
        description: 'Alignment with target audience interests and needs',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Irrelevant',
            2: 'Slightly relevant',
            3: 'Moderately relevant',
            4: 'Highly relevant',
            5: 'Perfectly targeted',
          },
        },
      },
      {
        id: 'persuasion',
        name: 'Persuasion',
        description: 'Effectiveness in driving desired action or response',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Not persuasive',
            2: 'Weakly persuasive',
            3: 'Moderately persuasive',
            4: 'Very persuasive',
            5: 'Extremely compelling',
          },
        },
      },
      {
        id: 'cta-clarity',
        name: 'CTA Clarity',
        description: 'Clear and actionable call-to-action',
        weight: 15,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'No clear CTA',
            2: 'Vague CTA',
            3: 'Acceptable CTA',
            4: 'Clear CTA',
            5: 'Compelling CTA',
          },
        },
      },
    ],
  },
  {
    id: 'visual-concept',
    name: 'Visual Concept',
    description: 'Evaluation of visual design concepts for advertising materials',
    criteria: [
      {
        id: 'aesthetic-quality',
        name: 'Aesthetic Quality',
        description: 'Overall visual appeal and design excellence',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Poor',
            2: 'Below average',
            3: 'Average',
            4: 'Above average',
            5: 'Exceptional',
          },
        },
      },
      {
        id: 'brand-consistency',
        name: 'Brand Consistency',
        description: 'Adherence to brand visual identity and guidelines',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Inconsistent',
            2: 'Weak consistency',
            3: 'Acceptable',
            4: 'Strong consistency',
            5: 'Perfect alignment',
          },
        },
      },
      {
        id: 'message-clarity',
        name: 'Message Clarity',
        description: 'How effectively the visual communicates the intended message',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Unclear',
            2: 'Somewhat clear',
            3: 'Moderately clear',
            4: 'Very clear',
            5: 'Crystal clear',
          },
        },
      },
      {
        id: 'emotional-impact',
        name: 'Emotional Impact',
        description: 'Ability to evoke desired emotional response',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'No impact',
            2: 'Weak impact',
            3: 'Moderate impact',
            4: 'Strong impact',
            5: 'Powerful impact',
          },
        },
      },
      {
        id: 'originality',
        name: 'Originality',
        description: 'Uniqueness and creative differentiation',
        weight: 10,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Generic',
            2: 'Derivative',
            3: 'Somewhat unique',
            4: 'Very unique',
            5: 'Highly original',
          },
        },
      },
    ],
  },
  {
    id: 'commercial-production',
    name: 'Commercial Production',
    description: 'Evaluation of video commercial production quality and effectiveness',
    criteria: [
      {
        id: 'narrative-coherence',
        name: 'Narrative Coherence',
        description: 'Logical flow and storytelling effectiveness',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Disjointed',
            2: 'Weak flow',
            3: 'Acceptable flow',
            4: 'Strong narrative',
            5: 'Seamless story',
          },
        },
      },
      {
        id: 'visual-quality',
        name: 'Visual Quality',
        description: 'Technical quality of cinematography and production',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Poor quality',
            2: 'Below standard',
            3: 'Acceptable',
            4: 'High quality',
            5: 'Professional grade',
          },
        },
      },
      {
        id: 'pacing',
        name: 'Pacing',
        description: 'Appropriate rhythm and timing throughout',
        weight: 15,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Too slow/fast',
            2: 'Uneven',
            3: 'Acceptable',
            4: 'Well-paced',
            5: 'Perfect timing',
          },
        },
      },
      {
        id: 'brand-presence',
        name: 'Brand Presence',
        description: 'Effective integration of brand elements',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Minimal',
            2: 'Weak presence',
            3: 'Adequate',
            4: 'Strong presence',
            5: 'Dominant presence',
          },
        },
      },
      {
        id: 'call-to-action',
        name: 'Call to Action',
        description: 'Clarity and effectiveness of CTA delivery',
        weight: 15,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Unclear/missing',
            2: 'Weak CTA',
            3: 'Acceptable',
            4: 'Clear CTA',
            5: 'Compelling CTA',
          },
        },
      },
    ],
  },
  {
    id: 'research-report',
    name: 'Research Report',
    description: 'Evaluation of market research report quality and actionability',
    criteria: [
      {
        id: 'depth',
        name: 'Depth',
        description: 'Thoroughness and comprehensiveness of analysis',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Superficial',
            2: 'Basic coverage',
            3: 'Adequate depth',
            4: 'Thorough',
            5: 'Comprehensive',
          },
        },
      },
      {
        id: 'accuracy',
        name: 'Accuracy',
        description: 'Correctness and reliability of information',
        weight: 25,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Inaccurate',
            2: 'Some errors',
            3: 'Mostly accurate',
            4: 'Very accurate',
            5: 'Fully verified',
          },
        },
      },
      {
        id: 'actionability',
        name: 'Actionability',
        description: 'Practical value and applicability of insights',
        weight: 20,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Not actionable',
            2: 'Limited value',
            3: 'Somewhat useful',
            4: 'Very actionable',
            5: 'Highly practical',
          },
        },
      },
      {
        id: 'citations',
        name: 'Citations',
        description: 'Quality and credibility of sources',
        weight: 15,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'No citations',
            2: 'Weak sources',
            3: 'Adequate sources',
            4: 'Strong sources',
            5: 'Authoritative',
          },
        },
      },
      {
        id: 'insight-quality',
        name: 'Insight Quality',
        description: 'Originality and value of analysis and conclusions',
        weight: 15,
        scale: {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'No insights',
            2: 'Basic insights',
            3: 'Good insights',
            4: 'Strong insights',
            5: 'Breakthrough',
          },
        },
      },
    ],
  },
];
