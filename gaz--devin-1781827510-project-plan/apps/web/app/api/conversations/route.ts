import { NextResponse } from "next/server";
import { getConversations } from "../../../lib/mvp-data";

export async function GET() {
  const result = await getConversations();
  if (result.state === "live") {
    return NextResponse.json(result.data);
  }
  return NextResponse.json([]);
}
