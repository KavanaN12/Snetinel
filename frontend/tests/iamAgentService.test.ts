// Runtime validation coverage for: IAM-agent API requests.
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock('../src/api/client', () => ({
  default: { get, post },
}));

import { iamAgentService } from '../src/services/sentinelApi';

describe('IAM-agent service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts a workspace run with the requested attempt limit', () => {
    iamAgentService.run('workspace-123', 2);

    expect(post).toHaveBeenCalledWith('/iam-agent/workspaces/workspace-123/run', {
      max_attempts: 2,
    });
  });

  it('uses the default attempt limit when none is specified', () => {
    iamAgentService.run('workspace-123');

    expect(post).toHaveBeenCalledWith('/iam-agent/workspaces/workspace-123/run', {
      max_attempts: 5,
    });
  });

  it('loads persisted run history for the selected workspace', () => {
    iamAgentService.listRuns('workspace-123');

    expect(get).toHaveBeenCalledWith('/iam-agent/workspaces/workspace-123/runs');
  });
});
