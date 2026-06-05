import { createResearchRun } from "@/lib/backend";
import { NextResponse } from "next/server";
import { z } from "zod";

const intakeSchema = z.object({
  nicheResearchTopic: z.string().min(1),
  whyICare: z.string().min(1),
  intendedUse: z.string().min(1),
  depth: z.enum(["Quick scan", "Standard brief", "Deep research", "Technical deep dive", "Custom"]),
  customDepth: z.string().optional(),
  currentSkillLevel: z
    .enum(["New to the topic", "Working knowledge", "Advanced builder", "Expert", "Mixed audience", ""])
    .optional(),
  deadline: z.string().optional(),
  outputType: z.string().optional(),
});

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = intakeSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "Required research intake fields are missing.", issues: parsed.error.issues },
      { status: 400 },
    );
  }

  if (parsed.data.depth === "Custom" && !parsed.data.customDepth?.trim()) {
    return NextResponse.json({ error: "customDepth is required for Custom depth." }, { status: 400 });
  }

  const run = await createResearchRun(parsed.data);
  return NextResponse.json(run);
}
