import { BackendRequestError, runUpdateAction } from "@/lib/backend";
import { NextResponse } from "next/server";
import { z } from "zod";

const actionSchema = z.object({
  action: z.enum(["approve", "decline"]),
  passcode: z.string().optional(),
});

export async function POST(request: Request, context: { params: Promise<{ updateId: string }> }) {
  const json = await request.json();
  const parsed = actionSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid update action." }, { status: 400 });
  }
  const { updateId } = await context.params;
  try {
    const response = await runUpdateAction(updateId, parsed.data.action, parsed.data.passcode);
    return NextResponse.json(response);
  } catch (error) {
    if (error instanceof BackendRequestError) {
      return NextResponse.json(error.payload, { status: error.status });
    }
    throw error;
  }
}
