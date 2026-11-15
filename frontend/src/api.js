export async function fetchAnalysis(lat, lon) {
  const response = await fetch(`/api/analysis?lat=${lat}&lon=${lon}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body && body.detail;
    throw new Error(
      typeof detail === "string" ? detail : `Request failed with status ${response.status}`
    );
  }

  return response.json();
}
