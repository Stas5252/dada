import { test, expect } from '@playwright/test';

test.describe('Testbed CRUD Flow Smoke Test', () => {
  test.use({ baseURL: 'http://127.0.0.1:8000' });

  let accessToken: string;
  let tenantId: string;
  let agentId: string;

  test.beforeAll(async ({ request }) => {
    // 1. Register a new user to get a token and tenant
    const uniqueEmail = `testbed_crud_${Date.now()}@example.com`;
    const registerResponse = await request.post('/api/v1/auth/register', {
      data: {
        company_name: 'Test Company',
        owner_name: 'Test Owner',
        owner_email: uniqueEmail,
        password: 'securepassword123'
      }
    });
    
    expect(registerResponse.ok()).toBeTruthy();
    const registerData = await registerResponse.json();
    accessToken = registerData.access_token;
    tenantId = registerData.tenant.id;

    // 2. Create an agent
    const agentResponse = await request.post('/api/v1/agents', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'x-tenant-id': tenantId
      },
      data: {
        name: 'Testbed Agent',
        prompt: 'You are a testing agent.',
        llm_provider: 'mock'
      }
    });

    expect(agentResponse.ok()).toBeTruthy();
    const agentData = await agentResponse.json();
    agentId = agentData.id;
  });

  test('should create, list, and run a test case', async ({ request }) => {
    // Create Test Case
    const createRes = await request.post(`/api/v1/agents/${agentId}/testbed/cases`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'x-tenant-id': tenantId
      },
      data: {
        name: 'Greeting Scenario',
        scenario: 'Greet the user',
        expected_outcome: 'Agent greets user warmly'
      }
    });
    expect(createRes.ok()).toBeTruthy();
    const testCase = await createRes.json();
    expect(testCase.name).toBe('Greeting Scenario');
    const testCaseId = testCase.id;

    // List Test Cases
    const listRes = await request.get(`/api/v1/agents/${agentId}/testbed/cases`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'x-tenant-id': tenantId
      }
    });
    expect(listRes.ok()).toBeTruthy();
    const testCases = await listRes.json();
    expect(testCases.length).toBeGreaterThan(0);
    expect(testCases[0].id).toBe(testCaseId);

    // Run Test Case
    const runRes = await request.post(`/api/v1/agents/${agentId}/testbed/cases/${testCaseId}/run`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'x-tenant-id': tenantId
      }
    });
    expect(runRes.ok()).toBeTruthy();
    const testRun = await runRes.json();
    expect(testRun.test_case_id).toBe(testCaseId);
    expect(testRun.status).toBe('running');
    const testRunId = testRun.id;

    // List Test Runs
    const listRunsRes = await request.get(`/api/v1/agents/${agentId}/testbed/runs`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'x-tenant-id': tenantId
      }
    });
    expect(listRunsRes.ok()).toBeTruthy();
    const testRuns = await listRunsRes.json();
    expect(testRuns.length).toBeGreaterThan(0);
    expect(testRuns[0].id).toBe(testRunId);
  });
});
