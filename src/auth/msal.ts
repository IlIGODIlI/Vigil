import {
  BrowserCacheLocation,
  PublicClientApplication,
  type Configuration,
  type RedirectRequest,
} from '@azure/msal-browser';

const clientId = import.meta.env.VITE_ENTRA_CLIENT_ID?.trim() ?? '';
const tenantId = import.meta.env.VITE_ENTRA_TENANT_ID?.trim() ?? '';
const redirectUri =
  import.meta.env.VITE_ENTRA_REDIRECT_URI?.trim() ||
  `${window.location.origin}/login`;

export const isEntraConfigured = Boolean(
  clientId && tenantId && redirectUri
);

const msalConfig: Configuration = {
  auth: {
    clientId,
    ...(tenantId
      ? {
          authority: `https://login.microsoftonline.com/${tenantId}`,
        }
      : {}),
    redirectUri,
    postLogoutRedirectUri: `${window.location.origin}/login`,
  },

  cache: {
    cacheLocation: BrowserCacheLocation.LocalStorage,
  },
};

export const loginRequest: RedirectRequest = {
  scopes: ['openid', 'profile', 'email'],
  redirectUri,
};

export const msalInstance = new PublicClientApplication(msalConfig);

let initPromise: Promise<void> | null = null;

export function ensureMsalInitialized(): Promise<void> {
  if (!initPromise) {
    initPromise = msalInstance.initialize();
  }

  return initPromise;
}

// Stores the current Microsoft access token only in memory.
let currentAccessToken: string | null = null;

export function getAccessToken(): string | null {
  return currentAccessToken;
}

export function setAccessToken(token: string | null): void {
  currentAccessToken = token;
}