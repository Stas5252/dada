"use server";

import { revalidatePath } from "next/cache";
import { mutateCoreApi } from "../../lib/core-api";

export async function sendOperatorMessageAction(conversationId: string, content: string) {
  if (!content.trim()) {
    return { error: "Message cannot be empty" };
  }

  const result = await mutateCoreApi(`/api/v1/conversations/${conversationId}/messages`, {
    content: content.trim(),
  });

  if (result.state === "live") {
    revalidatePath(`/conversations/${conversationId}`);
    return { success: true };
  }

  return { error: result.message || "Failed to send message" };
}

export async function resolveConversationAction(conversationId: string) {
  const result = await mutateCoreApi(`/api/v1/conversations/${conversationId}/resolve`, {});

  if (result.state === "live") {
    revalidatePath(`/conversations/${conversationId}`);
    revalidatePath("/conversations");
    return { success: true };
  }

  return { error: result.message || "Failed to resolve conversation" };
}

export async function handoffConversationAction(conversationId: string) {
  const result = await mutateCoreApi(`/api/v1/conversations/${conversationId}/handoff`, {});

  if (result.state === "live") {
    revalidatePath(`/conversations/${conversationId}`);
    revalidatePath("/conversations");
    return { success: true };
  }

  return { error: result.message || "Failed to escalate conversation" };
}
