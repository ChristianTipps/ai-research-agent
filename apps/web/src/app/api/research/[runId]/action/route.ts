import { runAction, saveFeedback } from "@/lib/backend";
import { NextResponse } from "next/server";

const allowedActions = new Set(["cancel", "retry", "resume"]);

export async function POST(request: Request, context: { params: Promise<{ runId: string }> }) {
  const { runId } = await context.params;
  const body = await request.json().catch(() => ({}));
  const action = String(body.action ?? "");

  if (action === "feedback") {
    const response = await saveFeedback(runId, {
      rating: typeof body.rating === "string" ? body.rating : undefined,
      comment: typeof body.comment === "string" ? body.comment : undefined,
    });
    return NextResponse.json(response);
  }

  if (!allowedActions.has(action)) {
    return NextResponse.json({ error: "Unsupported action." }, { status: 400 });
  }

  const response = await runAction(runId, action as "cancel" | "retry" | "resume");
  return NextResponse.json(response);
}
