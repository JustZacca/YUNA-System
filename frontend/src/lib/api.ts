
import type {
  LoginRequest,
  LoginResponse,
  User,
  SystemHealth,
  SystemStats,
  SearchResponse,
  SearchResult,
  AnimeListResponse,
  AnimeDetail,
  AnimeAddRequest,
  AnimeAddResponse
} from './types';

const API_BASE_URL = 'http://localhost:8000/api';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class YunaApiClient {
  private accessToken: string | null = null;

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken && { Authorization: `Bearer ${this.accessToken}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}`,
          response.status,
          response.statusText
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(
        'Network error occurred',
        0,
        'Network Error'
      );
    }
  }

  // Authentication
  async login(credentials: LoginRequest) {
    const data = await this.request<LoginResponse>('/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    
    this.accessToken = data.access_token;
    
    // Store token in localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('yuna_token', data.access_token);
    }
    
    return data;
  }

  logout(): void {
    this.accessToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('yuna_token');
    }
  }

  loadStoredToken(): void {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('yuna_token');
      if (token) {
        this.accessToken = token;
      }
    }
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/me');
  }

  // System
  async getHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/health');
  }

  async getStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/stats');
  }

  // Search
  async search(query: string, type: 'all' | 'anime' | 'series' | 'film' = 'all'): Promise<SearchResponse> {
    const params = new URLSearchParams({ q: query, type });
    return this.request<SearchResponse>(`/search?${params}`);
  }

  async searchAnimeJikan(query: string, limit: number = 10): Promise<SearchResult[]> {
    const params = new URLSearchParams({ q: query, limit: limit.toString() });
    return this.request<SearchResult[]>(`/search/anime/jikan?${params}`);
  }

  async getAnimeJikan(malId: number): Promise<SearchResult> {
    return this.request<SearchResult>(`/search/anime/jikan/${malId}`);
  }

  async getTopAnimeJikan(typeFilter?: string, limit: number = 10): Promise<SearchResult[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (typeFilter) params.append('type_filter', typeFilter);
    return this.request<SearchResult[]>(`/search/anime/jikan/top?${params}`);
  }

  async getSeasonalAnimeJikan(year?: number, season?: string, limit: number = 10): Promise<SearchResult[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (year) params.append('year', year.toString());
    if (season) params.append('season', season);
    return this.request<SearchResult[]>(`/search/anime/jikan/seasonal?${params}`);
  }

  // Anime Management
  async getAnimeList(): Promise<AnimeListResponse> {
    return this.request<AnimeListResponse>('/anime');
  }

  async getAnimeDetail(name: string): Promise<AnimeDetail> {
    return this.request<AnimeDetail>(`/anime/${encodeURIComponent(name)}`);
  }

  async addAnime(request: AnimeAddRequest): Promise<AnimeAddResponse> {
    return this.request<AnimeAddResponse>('/anime', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async deleteAnime(name: string): Promise<void> {
    return this.request<void>(`/anime/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
  }

  async downloadAnimeEpisodes(name: string, episodes?: number[]): Promise<any> {
    return this.request<any>(`/anime/${encodeURIComponent(name)}/download`, {
      method: 'POST',
      body: JSON.stringify({ episodes }),
    });
  }

  async getAnimeEpisodes(name: string): Promise<any> {
    return this.request<any>(`/anime/${encodeURIComponent(name)}/episodes`);
  }

  get isAuthenticated(): boolean {
    return !!this.accessToken;
  }
}

export const api = new YunaApiClient();

// Load stored token on client side
if (typeof window !== 'undefined') {
  api.loadStoredToken();
}