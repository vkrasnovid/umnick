import { ToolResponse } from './types.js';

export class ToolsApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://tools:8000') {
    this.baseUrl = baseUrl;
  }

  async execute(
    toolName: string,
    tenantId: string,
    params: Record<string, unknown>,
  ): Promise<ToolResponse> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15_000);

    try {
      // Build query params from the params object
      const queryParams = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          queryParams.set(key, String(value));
        }
      }
      const qs = queryParams.toString();
      const url = `${this.baseUrl}/tools/${toolName}${qs ? '?' + qs : ''}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'X-Tenant-Id': tenantId,
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorBody = await response.text();
        return {
          success: false,
          data: null,
          summary: '',
          error: `HTTP ${response.status}: ${errorBody}`,
        };
      }

      const data = await response.json();
      return data as ToolResponse;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return {
          success: false,
          data: null,
          summary: '',
          error: 'Таймаут запроса: сервер не ответил за 15 секунд',
        };
      }
      return {
        success: false,
        data: null,
        summary: '',
        error: `Ошибка соединения: ${(err as Error).message}`,
      };
    } finally {
      clearTimeout(timeout);
    }
  }
}
