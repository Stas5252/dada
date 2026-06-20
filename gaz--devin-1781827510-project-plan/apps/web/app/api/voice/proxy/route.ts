import { NextRequest, NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { getAccessToken } from "../../../../lib/auth";
import { getCoreTenantId } from "../../../../lib/core-api";

export async function POST(req: NextRequest) {
  const token = await getAccessToken();
  const tenantId = await getCoreTenantId();

  if (!token || !tenantId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const agentId = searchParams.get("agent_id");

  if (!agentId) {
    return NextResponse.json({ error: "agent_id is required" }, { status: 400 });
  }

  try {
    const formData = await req.formData();
    const audioFile = formData.get("audio");

    if (!audioFile) {
      return NextResponse.json({ error: "No audio file provided" }, { status: 400 });
    }

    // We generate a random session ID for testing
    const sessionId = uuidv4();

    // Create new FormData to send to FastAPI
    const backendFormData = new FormData();
    backendFormData.append("audio", audioFile);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    // POST /api/v1/voice/sessions/{session_id}/audio?agent_id={agent_id}
    const response = await fetch(`${apiUrl}/api/v1/voice/sessions/${sessionId}/audio?agent_id=${agentId}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "x-tenant-id": tenantId,
      },
      body: backendFormData,
    });

    if (!response.ok) {
      const text = await response.text();
      console.error("Backend Error:", text);
      return NextResponse.json({ error: "Backend error" }, { status: response.status });
    }

    // Return the audio blob back to the client
    const blob = await response.blob();
    return new NextResponse(blob, {
      headers: {
        "Content-Type": "audio/mpeg",
      },
    });
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
