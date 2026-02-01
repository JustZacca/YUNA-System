
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
  AnimeAddResponse,
  SeriesListResponse,
  SeriesDetail,
  FilmListResponse,
  FilmDetail
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
    // Ensure token is loaded from localStorage before making request
    if (!this.accessToken && typeof window !== 'undefined') {
      this.loadStoredToken();
    }

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
        
        // Log auth errors for debugging
        if (response.status === 401) {
          console.error('Authentication error:', {
            endpoint,
            hasToken: !!this.accessToken,
            error: errorData
          });
        }
        
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

	async refreshAnimeEpisodes(name: string): Promise<{ success: boolean; episodes_available: number; message: string }> {
		return this.request(`/anime/${encodeURIComponent(name)}/refresh-episodes`, {
			method: 'POST',
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

  async updateAnimeMetadata(name: string, anilistId: number): Promise<AnimeDetail> {
    return this.request<AnimeDetail>(`/anime/${encodeURIComponent(name)}`, {
      method: 'PATCH',
      body: JSON.stringify({ anilist_id: anilistId }),
    });
  }

  get isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // Series Management
  async getSeriesList(): Promise<SeriesListResponse> {
    return this.request<SeriesListResponse>('/series');
  }

  async getSeriesDetail(name: string): Promise<SeriesDetail> {
    return this.request<SeriesDetail>(`/series/${encodeURIComponent(name)}`);
  }

  async updateSeriesMetadata(name: string, tmdbId: number): Promise<SeriesDetail> {
    return this.request<SeriesDetail>(`/series/${encodeURIComponent(name)}/metadata`, {
      method: 'PATCH',
      body: JSON.stringify({ tmdb_id: tmdbId }),
    });
  }

  // Films Management
  async getFilmsList(): Promise<FilmListResponse> {
    return this.request<FilmListResponse>('/films');
  }

  async getFilmDetail(name: string): Promise<FilmDetail> {
    return this.request<FilmDetail>(`/films/${encodeURIComponent(name)}`);
  }

  async updateFilmMetadata(name: string, tmdbId: number): Promise<FilmDetail> {
    return this.request<FilmDetail>(`/films/${encodeURIComponent(name)}/metadata`, {
      method: 'PATCH',
      body: JSON.stringify({ tmdb_id: tmdbId }),
    });
  }

  // Delete Methods
  async deleteAnime(name: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/anime/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
  }

  async deleteSeries(name: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/series/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
  }

  async deleteFilm(name: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/films/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
  }
}

export const api = new YunaApiClient();

// Load stored token on client side
if (typeof window !== 'undefined') {
  api.loadStoredToken();
}