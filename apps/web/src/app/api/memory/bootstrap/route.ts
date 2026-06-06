import { bootstrapMemory } from "@/lib/backend";
import { NextResponse } from "next/server";
import { z } from "zod";

const bootstrapSchema = z.object({
  passcode: z.string().optional(),
});

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = bootstrapSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid bootstrap request." }, { status: 400 });
  }
  const memory = await bootstrapMemory(parsed.data.passcode);
  return NextResponse.json(memory);
}
