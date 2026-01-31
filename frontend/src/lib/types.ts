export interface User {
  username: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface SearchResult {
  name: string;
  type: string;
  year?: string;
  mal_id?: number;
  tmdb_id?: number;
  overview?: string;
  poster?: string;
  backdrop?: string;
  rating?: number;
  vote_count?: number;
  genres: string[];
  episodes?: number;
  seasons?: number;
  status?: string;
  runtime?: number;
  provider?: string;
  provider_url?: string;
  provider_id?: number;
  provider_slug?: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  anime: SearchResult[];
  series: SearchResult[];
  films: SearchResult[];
  tmdb_available: boolean;
  jikan_available: boolean;
}

export interface AnimeBase {
  name: string;
  link: string;
  episodes_downloaded: number;
  episodes_total: number;
  last_update?: string;
  mal_id?: number;
  synopsis?: string;
  rating?: number;
  year?: number;
  genres: string[];
  status?: string;
  poster_url?: string;
}

export interface AnimeListResponse {
  items: AnimeBase[];
  total: number;
}

export interface AnimeDetail extends AnimeBase {
  missing_episodes: number[];
  folder_path?: string;
}

export interface AnimeAddRequest {
  url: string;
}

export interface AnimeAddResponse {
  success: boolean;
  name: string;
  message: string;
}

export interface SystemStats {
  anime_count: number;
  series_count: number;
  films_count: number;
  total_episodes: number;
  storage_used: string;
}

export interface SystemHealth {
  status: string;
  api_version: string;
  uptime: number;
}