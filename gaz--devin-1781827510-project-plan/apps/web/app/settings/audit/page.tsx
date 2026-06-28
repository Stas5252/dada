import { fetchCoreApi, type CoreAuditLog } from "../../../lib/core-api";
import { AuditLogsList } from "../../components/AuditLogsList";

export const metadata = {
  title: "Audit Logs - CallForce",
};

async function getAuditLogs(): Promise<CoreAuditLog[]> {
  const result = await fetchCoreApi<CoreAuditLog[]>("/api/v1/audit-logs");
  if (result.state === "live") return result.data;
  return [];
}

export default async function AuditSettingsPage() {
  const logs = await getAuditLogs();

  return <AuditLogsList initialLogs={logs} />;
}
