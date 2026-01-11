export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  if (i === 0) return `${bytes} B`;
  if (i >= 3) return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`;
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

export function formatCost(bytes: number): string {
  const GB = 1024 * 1024 * 1024;
  const costPerGB = 0.023;
  const cost = (bytes / GB) * costPerGB;
  return `~$${cost.toFixed(2)}/month`;
}
