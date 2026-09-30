/**
 * Builds a public shareable link for a location's action plan and hands it
 * off to the device's native share sheet (WhatsApp/SMS/etc.) when available,
 * falling back to clipboard copy so people in the affected locality can open
 * it and follow the evacuation route themselves.
 */
export function buildShareUrl(locationId) {
  return `${window.location.origin}/share/${encodeURIComponent(locationId)}`;
}

export async function shareLocation(locationId, actionText) {
  const url = buildShareUrl(locationId);
  const shareData = {
    title: "ADIS Community Safety Alert",
    text: actionText ? `${actionText} — ${locationId}` : `Safety alert for ${locationId}`,
    url,
  };

  if (navigator.share) {
    try {
      await navigator.share(shareData);
      return "shared";
    } catch {
      // user cancelled the native share sheet -- not an error
      return "cancelled";
    }
  }

  if (navigator.clipboard) {
    await navigator.clipboard.writeText(url);
    return "copied";
  }

  window.prompt("Copy this link to share:", url);
  return "prompted";
}
