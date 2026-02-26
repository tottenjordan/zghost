import type { Session } from '../../types/session';
import type { SearchTrend, YTTrend } from '../../types/trends';
import type { AgentEvent, AgentState, OrchestrationStatus } from '../../types/agents';
import type { Rubric, Rating, ArtifactRating } from '../../types/rating';
import type { ImageArtifact, VideoArtifact, CommercialArtifact } from '../../types/artifacts';

// Mock Session (frontend format, after mapping from ADK)
export const mockSession: Session = {
  session_id: 'test-session-123',
  app_name: 'trends_and_insights_agent',
  user_id: 'test-user',
  created_at: '2024-01-01T00:00:00Z',
  state: {
    brand: 'Google',
    target_product: 'Pixel 9',
    target_audience: 'Tech enthusiasts aged 25-40',
    key_selling_points: 'Advanced AI features, Pro camera',
    target_search_trends: { target_search_trends: [] },
    target_yt_trends: { target_yt_trends: [] },
    img_artifact_keys: { img_artifact_keys: [] },
    vid_artifact_keys: { vid_artifact_keys: [] },
    commercial_artifact: '',
    combined_final_cited_report: '',
    sources: {},
    gcs_folder: 'test-folder',
  },
  events: [],
};

// Mock ADK session response (ADK server format, before mapping)
export const mockAdkSession = {
  id: 'test-session-123',
  appName: 'trends_and_insights_agent',
  userId: 'test-user',
  createdAt: '2024-01-01T00:00:00Z',
  state: {
    brand: 'Google',
    target_product: 'Pixel 9',
    target_audience: 'Tech enthusiasts aged 25-40',
    key_selling_points: 'Advanced AI features, Pro camera',
    target_search_trends: { target_search_trends: [] },
    target_yt_trends: { target_yt_trends: [] },
    img_artifact_keys: { img_artifact_keys: [] },
    vid_artifact_keys: { vid_artifact_keys: [] },
    commercial_artifact: '',
    combined_final_cited_report: '',
    sources: {},
    gcs_folder: 'test-folder',
  },
  events: [],
};

// Mock Search Trends
export const mockSearchTrends: SearchTrend[] = [
  {
    rank: 1,
    title: 'AI Photography',
    formattedTraffic: '500K+',
    relatedQueries: 'AI camera, computational photography',
    traffic: '500000',
    exploreLink: 'https://trends.google.com/trends/explore?q=AI+Photography',
    image: {
      newsUrl: 'https://news.example.com/ai-photo',
      source: 'Tech News',
      imageUrl: 'https://example.com/image.jpg',
    },
    articles: [
      {
        title: 'AI Photography Takes Over',
        timeAgo: '2 hours ago',
        source: 'Tech Blog',
        snippet: 'AI is revolutionizing smartphone photography...',
        url: 'https://example.com/article',
      },
    ],
    shareUrl: 'https://trends.google.com/share',
  },
  {
    rank: 2,
    title: 'Smartphone Innovation',
    formattedTraffic: '300K+',
    relatedQueries: 'new phones, flagship devices',
    traffic: '300000',
  },
];

// Mock YouTube Trends
export const mockYTTrends: YTTrend[] = [
  {
    rank: 1,
    title: 'Pixel 9 Pro Review - Best Camera Yet?',
    videoId: 'abc123',
    videoUrl: 'https://youtube.com/watch?v=abc123',
    channelName: 'Tech Reviews',
    channelUrl: 'https://youtube.com/c/techreviews',
    description: 'In-depth review of the Google Pixel 9 Pro camera system',
    viewCount: '1.2M',
    publishedTime: '2 days ago',
    thumbnail: 'https://i.ytimg.com/vi/abc123/default.jpg',
  },
  {
    rank: 2,
    title: 'AI Features on Pixel 9',
    videoId: 'def456',
    videoUrl: 'https://youtube.com/watch?v=def456',
    channelName: 'Mobile Tech',
    channelUrl: 'https://youtube.com/c/mobiletech',
    description: 'Exploring the new AI capabilities',
    viewCount: '850K',
    publishedTime: '1 week ago',
  },
];

// Mock Agent Events
export const mockAgentEvents: AgentEvent[] = [
  {
    type: 'agent_start',
    agentName: 'trends_and_insights_agent',
    data: { message: 'Starting trend analysis' },
    timestamp: Date.now() - 10000,
  },
  {
    type: 'tool_call',
    agentName: 'trends_and_insights_agent',
    data: { tool: 'fetch_trends', args: {} },
    timestamp: Date.now() - 8000,
  },
  {
    type: 'tool_response',
    agentName: 'trends_and_insights_agent',
    data: { result: 'Trends fetched successfully' },
    timestamp: Date.now() - 6000,
  },
  {
    type: 'agent_complete',
    agentName: 'trends_and_insights_agent',
    data: { status: 'completed' },
    timestamp: Date.now() - 2000,
  },
];

// Mock Agent State
export const mockAgentState: AgentState = {
  name: 'trends_and_insights_agent',
  status: 'running',
  startTime: Date.now() - 10000,
};

// Mock Orchestration Status
export const mockOrchestrationStatus: OrchestrationStatus = {
  sessionId: 'test-session-123',
  pipelineStatus: 'running',
  agents: {
    trends_and_insights_agent: {
      status: 'completed',
      startTime: Date.now() - 20000,
      endTime: Date.now() - 10000,
    },
    research_orchestrator: {
      status: 'running',
      startTime: Date.now() - 8000,
    },
    ad_content_generator: {
      status: 'idle',
    },
  },
  startedAt: new Date(Date.now() - 20000).toISOString(),
};

// Mock Rubric
export const mockRubric: Rubric = {
  id: 'rubric-1',
  name: 'Ad Quality Rubric',
  description: 'Evaluate advertising content quality',
  criteria: [
    {
      id: 'relevance',
      name: 'Relevance',
      description: 'How relevant is the content to the target audience?',
      weight: 0.3,
      minScore: 1,
      maxScore: 5,
    },
    {
      id: 'creativity',
      name: 'Creativity',
      description: 'How creative and engaging is the content?',
      weight: 0.3,
      minScore: 1,
      maxScore: 5,
    },
    {
      id: 'clarity',
      name: 'Clarity',
      description: 'How clear is the message?',
      weight: 0.4,
      minScore: 1,
      maxScore: 5,
    },
  ],
};

// Mock Ratings
export const mockRatings: Rating[] = [
  { criterionId: 'relevance', score: 4, comment: 'Very relevant' },
  { criterionId: 'creativity', score: 5, comment: 'Excellent creativity' },
  { criterionId: 'clarity', score: 3, comment: 'Could be clearer' },
];

// Mock Artifact Rating
export const mockArtifactRating: ArtifactRating = {
  artifactId: 'artifact-1',
  rubricId: 'rubric-1',
  ratings: mockRatings,
  overallScore: 4.0,
  ratedBy: 'test-user',
  ratedAt: '2024-01-01T12:00:00Z',
};

// Mock Image Artifact
export const mockImageArtifact: ImageArtifact = {
  id: 'img-1',
  type: 'image',
  url: 'https://storage.googleapis.com/bucket/image.png',
  gcsKey: 'session-123/image.png',
  width: 1024,
  height: 768,
  prompt: 'A futuristic smartphone with AI features',
  createdAt: '2024-01-01T10:00:00Z',
};

// Mock Video Artifact
export const mockVideoArtifact: VideoArtifact = {
  id: 'vid-1',
  type: 'video',
  url: 'https://storage.googleapis.com/bucket/video.mp4',
  gcsKey: 'session-123/video.mp4',
  duration: 15,
  prompt: 'A product showcase video',
  createdAt: '2024-01-01T11:00:00Z',
};

// Mock Commercial Artifact
export const mockCommercialArtifact: CommercialArtifact = {
  id: 'comm-1',
  type: 'commercial',
  url: 'https://storage.googleapis.com/bucket/commercial.mp4',
  gcsKey: 'session-123/commercial.mp4',
  duration: 30,
  scenes: [
    { startTime: 0, endTime: 10, description: 'Product introduction' },
    { startTime: 10, endTime: 20, description: 'Feature showcase' },
    { startTime: 20, endTime: 30, description: 'Call to action' },
  ],
  createdAt: '2024-01-01T12:00:00Z',
};
