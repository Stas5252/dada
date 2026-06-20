export type Channel = "telegram" | "web_widget" | "sip" | "whatsapp" | "vk";

export type MessageEvent = {
  tenantId: string;
  conversationId: string;
  channel: Channel;
  role: "customer" | "agent" | "operator" | "system";
  content: string;
  receivedAt: string;
};
