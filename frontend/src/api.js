export async function fetchAllData() {
  const response = await fetch("/api/data");
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}