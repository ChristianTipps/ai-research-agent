import { createResearchRun } from "@/lib/backend";
import { NextResponse } from "next/server";
import { z } from "zod";

function normalizeYoutubeUrls(value: unknown) {
  if (value === undefined || value === null || value === "") return undefined;
  const values = Array.isArray(value) ? value : [value];
  const urls = values
    .flatMap((item) => String(item).match(/https?:\/\/[^\s,]+|www\.youtube\.com\/[^\s,]+|youtube\.com\/[^\s,]+|youtu\.be\/[^\s,]+/gi) ?? String(item).split(/[\s,]+/))
    .map((item) => cleanYoutubeUrl(item))
    .filter((item): item is string => Boolean(item));
  return Array.from(new Set(urls.map((url) => url.toLowerCase()))).map(
    (lowercaseUrl) => urls.find((url) => url.toLowerCase() === lowercaseUrl) ?? lowercaseUrl,
  );
}

function cleanYoutubeUrl(value: string) {
  let candidate = value.trim().replace(/^[()[\]{}<>.,;"']+|[()[\]{}<>.,;"']+$/g, "");
  if (!candidate) return null;
  if (candidate.startsWith("www.")) {
    candidate = `https://${candidate}`;
  } else if (candidate.startsWith("youtube.com/") || candidate.startsWith("youtu.be/")) {
    candidate = `https://${candidate}`;
  }
  try {
    const url = new URL(candidate);
    if (!["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"].includes(url.hostname.toLowerCase())) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

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
  researchBudgetMinutes: z.number().int().min(1).max(60).optional(),
  outputType: z.string().optional(),
  youtubeUrls: z.preprocess(normalizeYoutubeUrls, z.array(z.string().url()).max(12)).optional(),
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
