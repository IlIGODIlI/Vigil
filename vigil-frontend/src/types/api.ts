export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  message: string;
  detail?: string | Record<string, unknown> | Array<{ loc?: string[]; msg?: string; type?: string }>;
  status?: number;
}
