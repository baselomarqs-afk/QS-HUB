// Protected /cache URLs must NEVER carry session tokens in query strings.
// Use <AuthImage src={url} /> which sends the Authorization: Bearer header via fetch.
export function cacheUrl(url) {
  return url || '';
}
