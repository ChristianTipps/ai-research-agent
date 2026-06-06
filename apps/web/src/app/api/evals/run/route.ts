import { runEvals } from "@/lib/backend";
import { NextResponse } from "next/server";
import { z } from "zod";

const evalRunSchema = z.object({
  runId: z.string().optional(),
  passcode: z.string().optional(),
});

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = evalRunSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid eval run request." }, { status: 400 });
  }
  const evals = await runEvals(parsed.data);
  return NextResponse.json(evals);
}
