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
  mal_id?: number;  // Keep for compatibility, same as anilist_id
  anilist_id?: number;
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
  anilist_available: boolean;
}

export interface AnimeBase {
  name: string;
  link: string;
  episodes_downloaded: number;
  episodes_total: number;
  last_update?: string;
  anilist_id?: number;
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
  episodes_available?: number;  // Episodes available on AnimeWorld
  folder_path?: string;
  poster?: string;  // Alias for poster_url for compatibility
}

// Series types
export interface SeriesBase {
  name: string;
  link: string;
  episodes_downloaded: number;
  episodes_total: number;
  last_update?: string;
  provider?: string;
  year?: number;
  // TMDB metadata
  tmdb_id?: number;
  overview?: string;
  poster_url?: string;
  backdrop_url?: string;
  rating?: number;
  genres?: string[];
  status?: string;
}

export interface SeriesListResponse {
  items: SeriesBase[];
  total: number;
}

export interface SeriesDetail extends SeriesBase {
  slug?: string;
  media_id?: number;
  provider_language?: string;
  seasons_data?: string;
  // TMDB metadata
  tmdb_id?: number;
  overview?: string;
  poster_path?: string;
  backdrop_path?: string;
  vote_average?: number;
  genre_ids?: number[];
}

// Film types
export interface FilmBase {
  name: string;
  link: string;
  downloaded: boolean;
  last_update?: string;
  provider?: string;
  year?: number;
  // TMDB metadata
  tmdb_id?: number;
  overview?: string;
  poster_url?: string;
  backdrop_url?: string;
  rating?: number;
  genres?: string[];
  runtime?: number;
}

export interface FilmListResponse {
  items: FilmBase[];
  total: number;
}

export interface FilmDetail extends FilmBase {
  slug?: string;
  media_id?: number;
  provider_language?: string;
  // TMDB metadata
  tmdb_id?: number;
  overview?: string;
  poster_path?: string;
  backdrop_path?: string;
  vote_average?: number;
  genre_ids?: number[];
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

// Provider search results
export interface ProviderSearchResult {
  title: string;
  provider: string;
  url?: string;
  poster?: string;
  slug?: string;
  media_id?: number;
  episodes?: number;
  year?: number;
  type?: string;
}

// Add content requests
export interface AddFromMetadataRequest {
  anilist_id?: number;
  tmdb_id?: number;
}

export interface AssociateProviderRequest {
  provider_url?: string;
  provider?: string;
  provider_slug?: string;
  media_id?: number;
}