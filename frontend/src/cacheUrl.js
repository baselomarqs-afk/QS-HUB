// Appends the session token to protected /cache image URLs so the authenticated
// /cache route can verify the viewer owns the project. <img> tags can't send
// Authorization headers, so the token rides as a query param instead.
export function cacheUrl(url) {
  if (!url || typeof url !== 'string' || !url.startsWith('/cache/')) return url;
  const token = localStorage.getItem('qto_token') || '';
  if (!token) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}token=${encodeURIComponent(token)}`;
}
