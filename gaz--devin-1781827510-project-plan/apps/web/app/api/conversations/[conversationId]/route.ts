import { NextRequest, NextResponse } from "next/server";
import { getConversationDetail } from "../../../../lib/mvp-data";

type Props = {
  params: Promise<{
    conversationId: string;
  }>;
};

export async function GET(req: NextRequest, { params }: Props) {
  const { conversationId } = await params;
  const result = await getConversationDetail(conversationId);
  if (result.state === "live" && result.data) {
    return NextResponse.json(result.data);
  }
  return NextResponse.json(null, { status: 404 });
}
