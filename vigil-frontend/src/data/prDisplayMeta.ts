export interface ChangedFile {
  filename: string;
  additions: number;
  deletions: number;
  status: 'added' | 'modified' | 'removed';
  patch: string; // The diff content
}

export interface PRDisplayMeta {
  files_changed: number;
  additions: number;
  deletions: number;
  files: ChangedFile[];
}

// Map of prId to display metadata
export const MOCK_PR_META: Record<string, PRDisplayMeta> = {
  // Using UUIDs from the API or a fallback for missing IDs
  default: {
    files_changed: 3,
    additions: 124,
    deletions: 42,
    files: [
      {
        filename: 'src/auth/jwt.ts',
        additions: 45,
        deletions: 12,
        status: 'modified',
        patch: `@@ -45,12 +45,45 @@
- // Deprecated token generation
- function signToken(user) {
-   return jwt.sign(user, 'secret');
- }
+ // Secure token generation with rotating keys
+ import { getPrivateKey } from './kms';
+ 
+ async function signToken(user) {
+   const key = await getPrivateKey();
+   return jwt.sign(
+     { sub: user.id, role: user.role }, 
+     key, 
+     { algorithm: 'RS256', expiresIn: '1h' }
+   );
+ }`
      },
      {
        filename: 'src/api/routes.ts',
        additions: 79,
        deletions: 30,
        status: 'modified',
        patch: `@@ -112,5 +112,12 @@
- router.post('/upload', uploadHandler);
+ // Added file type validation middleware
+ import { validateMimeType } from '../middleware/upload';
+ 
+ router.post('/upload', validateMimeType(['image/png', 'application/pdf']), uploadHandler);`
      }
    ]
  }
};

export function getPRDisplayMeta(prId: string): PRDisplayMeta {
  // If we have specific mock data for the UUID, return it. Otherwise return default.
  return MOCK_PR_META[prId] || MOCK_PR_META['default'];
}
