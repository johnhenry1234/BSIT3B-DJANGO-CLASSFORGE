/**
 * Typed client for the ClassForge JSON API v1.
 *
 * The client never stores credentials itself: callers pass a bearer token in
 * and are responsible for keeping it in VS Code SecretStorage.  ``fetch`` is
 * injectable so the client can be tested without a server.
 */

export interface CourseSummary {
  id: number;
  code: string;
  name: string;
  instructor: string;
  assignment_count: number;
}

export interface AssignmentSummary {
  id: number;
  title: string;
  course: { id: number; code: string; name: string };
  category: string;
  status: string;
  due_date: string | null;
  max_score: string | null;
  guidelines: string;
  required_files: string[];
  required_directories: string[];
  accepted_formats: string[];
  documentation_requirements: string;
  validation_rules: string[];
  required_tests: string[];
  max_upload_mb: number;
  ai_grading_mode: string;
  manual_review_required: boolean;
  allow_resubmission: boolean;
  default_exclusions: string[];
  rubric_total_points: string | null;
}

export interface RubricCriterionSummary {
  id: number;
  name: string;
  description: string;
  max_points: string | null;
  expected_evidence: string;
  validation_rule: string;
}

export interface AssignmentDetail extends AssignmentSummary {
  rubric: RubricCriterionSummary[];
  published_rubric_version: {
    id: number;
    version: number;
    total_points: string;
    published_at: string;
  } | null;
  project: ProjectSummary | null;
}

export interface SnapshotSummary {
  id: number;
  project_id: number;
  version: number;
  source: string;
  branch: string;
  file_count: number;
  total_bytes: number;
  checksum: string;
  commit_sha: string;
  created_at: string;
  note: string;
}

export interface ProjectSummary {
  id: number;
  title: string;
  status: string;
  latest_snapshot: SnapshotSummary | null;
  open_revisions: number;
  open_pull_requests: number;
}

export interface AssessmentSummary {
  id: number;
  snapshot_id: number;
  status: string;
  engine: string;
  model_name: string;
  mode: string;
  score: string | null;
  max_score: string | null;
  instructor_score: string | null;
  summary: string;
  feedback: string;
  requires_review: boolean;
  review_status: string;
  error: string;
  attempts: number;
  criteria: CriterionAssessmentSummary[];
}

export interface CriterionAssessmentSummary {
  id: number;
  criterion_id: number | null;
  name: string;
  max_points: string | null;
  ai_points: string | null;
  instructor_points: string | null;
  points: string | null;
  comment: string;
  evidence: string;
  confidence: string | null;
}

export interface RevisionRequestSummary {
  id: number;
  project_id: number;
  snapshot_id: number | null;
  title: string;
  description: string;
  branch_name: string;
  due_date: string | null;
  status: string;
  requested_by: number | null;
  created_at: string;
  resolved_at: string | null;
}

export interface FeedbackPayload {
  assessment: (AssessmentSummary & Record<string, unknown>) | null;
  grade: {
    id: number;
    score: string;
    max_score: string;
    feedback: string;
    is_published: boolean;
    graded_at: string | null;
  } | null;
}

export interface UserSummary {
  id: number;
  username: string;
  name: string;
  email: string;
  is_instructor: boolean;
  is_teaching_assistant: boolean;
}

export interface UploadFile {
  /** POSIX relative path, e.g. ``src/app.py``. */
  path: string;
  content: Uint8Array;
}

export interface UploadOptions {
  note?: string;
  branch?: string;
  createSubmission?: boolean;
  ignoreFile?: { name: string; content: Uint8Array };
}

export interface UploadResult {
  project: ProjectSummary;
  snapshot: SnapshotSummary & { manifest: ManifestEntry[] };
  submission: { id: number; version: number; is_late: boolean } | null;
  assessment: AssessmentSummary | null;
}

export interface ManifestEntry {
  path: string;
  size: number;
  sha256: string;
  extension: string;
}

export class ClassForgeApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly payload?: unknown,
  ) {
    super(message);
    this.name = 'ClassForgeApiError';
  }
}

export interface ClientOptions {
  baseUrl: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

type Json = Record<string, unknown>;

export class ClassForgeClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;
  private token: string | undefined;

  constructor(options: ClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch;
    this.timeoutMs = options.timeoutMs ?? 120_000;
    if (!this.baseUrl) {
      throw new Error('ClassForge server URL is not configured.');
    }
    if (typeof this.fetchImpl !== 'function') {
      throw new Error('This VS Code build does not provide fetch().');
    }
  }

  setToken(token: string | undefined): void {
    this.token = token || undefined;
  }

  hasToken(): boolean {
    return Boolean(this.token);
  }

  async createToken(username: string, password: string, name = 'VS Code extension'): Promise<string> {
    const payload = await this.request<{ token: string }>('POST', '/auth/token/', {
      body: { username, password, name },
      authenticated: false,
    });
    return payload.token;
  }

  async me(): Promise<{ user: UserSummary; scopes: string[]; limits: Json }> {
    return this.request('GET', '/me/');
  }

  async listCourses(): Promise<CourseSummary[]> {
    const data = await this.request<{ courses: CourseSummary[] }>('GET', '/courses/');
    return data.courses;
  }

  async listAssignments(courseId?: number): Promise<AssignmentSummary[]> {
    const suffix = courseId ? `?course=${encodeURIComponent(String(courseId))}` : '';
    const data = await this.request<{ assignments: AssignmentSummary[] }>(
      'GET',
      `/assignments/${suffix}`,
    );
    return data.assignments;
  }

  async assignmentDetail(assignmentId: number): Promise<AssignmentDetail> {
    const data = await this.request<{ assignment: AssignmentDetail }>(
      'GET',
      `/assignments/${assignmentId}/`,
    );
    return data.assignment;
  }

  async listProjects(): Promise<ProjectSummary[]> {
    const data = await this.request<{ projects: ProjectSummary[] }>('GET', '/projects/');
    return data.projects;
  }

  async projectDetail(projectId: number): Promise<{
    project: ProjectSummary;
    snapshots: SnapshotSummary[];
    revision_requests: RevisionRequestSummary[];
  }> {
    return this.request('GET', `/projects/${projectId}/`);
  }

  async submitFiles(
    assignmentId: number,
    files: UploadFile[],
    options: UploadOptions = {},
  ): Promise<UploadResult> {
    if (!files.length) {
      throw new Error('There are no files to submit.');
    }
    const form = new FormData();
    for (const file of files) {
      const name = file.path.split('/').pop() || 'file';
      form.append(
        'files[]',
        new Blob([file.content as unknown as BlobPart], { type: 'application/octet-stream' }),
        name,
      );
    }
    form.append('paths', JSON.stringify(files.map((file) => file.path)));
    form.append('source', 'vscode');
    form.append('create_submission', options.createSubmission === false ? '0' : '1');
    if (options.note) {
      form.append('note', options.note);
    }
    if (options.branch) {
      form.append('branch', options.branch);
    }
    if (options.ignoreFile) {
      form.append(
        'classforgeignore',
        new Blob([options.ignoreFile.content as unknown as BlobPart], { type: 'text/plain' }),
        options.ignoreFile.name,
      );
    }
    return this.request<UploadResult>('POST', `/assignments/${assignmentId}/submit/`, {
      body: form,
    });
  }

  async snapshotStatus(snapshotId: number): Promise<{
    snapshot: SnapshotSummary;
    assessment: AssessmentSummary | null;
  }> {
    return this.request('GET', `/snapshots/${snapshotId}/status/`);
  }

  async snapshotFeedback(snapshotId: number): Promise<FeedbackPayload> {
    return this.request('GET', `/snapshots/${snapshotId}/feedback/`);
  }

  async requestAssessment(snapshotId: number): Promise<AssessmentSummary> {
    const data = await this.request<{ assessment: AssessmentSummary }>(
      'POST',
      `/snapshots/${snapshotId}/assess/`,
      { body: {} },
    );
    return data.assessment;
  }

  async listRevisions(projectId: number): Promise<RevisionRequestSummary[]> {
    const data = await this.request<{ revision_requests: RevisionRequestSummary[] }>(
      'GET',
      `/projects/${projectId}/revisions/`,
    );
    return data.revision_requests;
  }

  async listNotifications(): Promise<{ unread: number; notifications: Json[] }> {
    return this.request('GET', '/notifications/');
  }

  async health(): Promise<Json> {
    return this.request('GET', '/health/', { authenticated: false });
  }

  private async request<T>(
    method: 'GET' | 'POST',
    path: string,
    options: { body?: unknown; authenticated?: boolean } = {},
  ): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    const authenticated = options.authenticated !== false;
    if (authenticated) {
      if (!this.token) {
        throw new ClassForgeApiError('Sign in to ClassForge first.', 401);
      }
      headers.Authorization = `Bearer ${this.token}`;
    }

    let body: BodyInit | undefined;
    if (options.body instanceof FormData) {
      body = options.body;
    } else if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}/api/v1${path}`, {
        method,
        headers,
        body,
        signal: controller.signal,
      });
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new ClassForgeApiError('The ClassForge request timed out.', 0);
      }
      throw new ClassForgeApiError(
        `Could not reach the ClassForge server: ${error instanceof Error ? error.message : String(error)}`,
        0,
      );
    } finally {
      clearTimeout(timeout);
    }

    const text = await response.text();
    let payload: unknown = undefined;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = text;
      }
    }
    if (!response.ok) {
      const message =
        payload && typeof payload === 'object' && 'error' in payload
          ? String((payload as Json).error)
          : `ClassForge request failed (HTTP ${response.status}).`;
      throw new ClassForgeApiError(message, response.status, payload);
    }
    return (payload ?? {}) as T;
  }
}
